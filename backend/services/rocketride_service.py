import asyncio
import logging
import os
from dotenv import load_dotenv
load_dotenv()
from pathlib import Path
from typing import Any, Protocol

from backend.models.entities import Bid
from backend.utils.config import get_settings


logger = logging.getLogger(__name__)

AI_UNAVAILABLE = "AI processing temporarily unavailable."
DIRECT_GROQ_MODEL = "openai/gpt-oss-20b"


class PipelineService(Protocol):
    async def analyze(self, bid: Bid, document: bytes) -> dict[str, Any]: ...

    async def generate(self, bid: Bid, document: bytes) -> dict[str, Any]: ...


class RocketRideServiceError(RuntimeError):
    """A sanitized error raised when RocketRide execution is unavailable."""


def _describe(exc: BaseException) -> str:
    # Exception class and a short message only: never tracebacks, headers or env values.
    return f"{type(exc).__name__}: {str(exc)[:200]}"


class RocketRideService:
    def __init__(self, pipeline_path: Path | None = None) -> None:
        self._pipeline_path = pipeline_path or Path(__file__).resolve().parents[2] / "bid_factory.pipe"

    async def analyze(self, bid: Bid, document: bytes) -> dict[str, Any]:
        return await self._execute(bid, document)

    async def generate(self, bid: Bid, document: bytes) -> dict[str, Any]:
        return await self._execute(bid, document)

    async def _execute(self, bid: Bid, document: bytes) -> dict[str, Any]:
        content_type = bid.rfp.content_type or ""
        if content_type.startswith("image/"):
            # The pipeline has no OCR stage, so scanned images always take the direct route.
            logger.info("bid=%s image upload: using direct OCR + Groq extraction", bid.id)
            return await self._direct_extraction(bid, document)

        try:
            return await self._run_pipeline(bid, document)
        except Exception as exc:
            logger.warning("bid=%s RocketRide request failed: %s", bid.id, _describe(exc))
            if not get_settings().ai_fallback_direct_groq:
                raise RocketRideServiceError(AI_UNAVAILABLE) from exc
            logger.info("bid=%s fallback started: direct Groq extraction (AI_FALLBACK_DIRECT_GROQ=true)", bid.id)
            return await self._direct_extraction(bid, document)

    async def _run_pipeline(self, bid: Bid, document: bytes) -> dict[str, Any]:
        try:
            from rocketride import RocketRideClient
        except ImportError as exc:
            raise RocketRideServiceError("RocketRide SDK is not installed.") from exc

        if not self._pipeline_path.is_file():
            raise RocketRideServiceError("BidFactory pipeline file was not found.")
        if not os.getenv("ROCKETRIDE_URI") or not os.getenv("ROCKETRIDE_APIKEY"):
            raise RocketRideServiceError("ROCKETRIDE_URI / ROCKETRIDE_APIKEY are not configured.")

        logger.info("bid=%s RocketRide request started", bid.id)
        client = RocketRideClient()
        token: str | None = None
        try:
            await client.connect()
            execution = await client.use(filepath=str(self._pipeline_path))
            token = execution.get("token")
            if not isinstance(token, str) or not token:
                raise RocketRideServiceError("RocketRide did not return a pipeline token.")

            try:
                result = await asyncio.wait_for(client.send(
                    token,
                    document,
                    objinfo={
                        "bid_id": str(bid.id),
                        "filename": bid.rfp.filename,
                    },
                    mimetype=bid.rfp.content_type,
                ), timeout=get_settings().rocketride_timeout_seconds)
            except asyncio.TimeoutError as exc:
                raise RocketRideServiceError("Timed out waiting for the RocketRide pipeline.") from exc

            logger.info("bid=%s RocketRide request succeeded", bid.id)
            return {
                "status": "completed",
                "message": "RocketRide pipeline completed.",
                "data": result,
            }
        finally:
            if token:
                try:
                    await client.terminate(token)
                except Exception:
                    pass
            try:
                await client.disconnect()
            except Exception:
                pass

    async def _direct_extraction(self, bid: Bid, document: bytes) -> dict[str, Any]:
        """Extract text locally and ask Groq for requirements. Raises on any failure."""
        from backend.services.document_ingestion import DocumentIngestionService

        api_key = os.getenv("ROCKETRIDE_GROQ_KEY")
        if not api_key:
            logger.error("bid=%s direct extraction failed: ROCKETRIDE_GROQ_KEY is not set", bid.id)
            raise RocketRideServiceError(AI_UNAVAILABLE)

        try:
            ext = os.path.splitext(bid.rfp.filename.lower())[1]
            if ext == '.pdf':
                pages = DocumentIngestionService._extract_pdf(document)
            elif ext in ['.png', '.jpg', '.jpeg']:
                pages = DocumentIngestionService._extract_image(document)
            else:
                pages = DocumentIngestionService._extract_docx(document)
            extracted_text = "".join(p.get("text", "") + "\n" for p in pages)

            import groq
            g_client = groq.Groq(api_key=api_key)
            completion = await asyncio.to_thread(
                g_client.chat.completions.create,
                model=DIRECT_GROQ_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a requirement extraction AI designed for processing RFPs and Bids. Extract a concise, definitive list of requirements from the provided RFP text. Output each requirement as a single sentence starting with 'The vendor must' or 'The system must'. Make sure to list all distinct requirements found in the text."
                    },
                    {
                        "role": "user",
                        "content": extracted_text[:15000] # truncate to avoid token limits
                    }
                ],
                temperature=0.1,
                max_tokens=1024,
            )
            generated_text = completion.choices[0].message.content
            if not generated_text or not generated_text.strip():
                raise ValueError("Groq returned an empty completion.")
        except Exception as exc:
            logger.error("bid=%s direct extraction failed: %s", bid.id, _describe(exc))
            raise RocketRideServiceError(AI_UNAVAILABLE) from exc

        logger.info("bid=%s direct extraction succeeded", bid.id)
        return {
            "status": "completed",
            "message": "Direct Groq extraction completed (RocketRide pipeline not used).",
            "data": {
                "text": generated_text
            }
        }


rocketride_service: PipelineService = RocketRideService()
