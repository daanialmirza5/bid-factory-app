"""Smoke-test bid_factory.pipe on the RocketRide development connection.

Run from the workspace root:  python -m scripts.rr_pipeline_check [document]
Sends the document the same way the backend does (locally extracted text plus
extraction instructions, as text/plain) and validates the result with the
backend's requirement extractor. Reads ROCKETRIDE_URI / ROCKETRIDE_APIKEY from
.env. Never prints secrets.
"""
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv
from rocketride import RocketRideClient

from backend.services.requirement_extraction import StructuredAIRequirementExtractor
from backend.services.rocketride_service import build_pipeline_payload, extract_text

ROOT = Path(__file__).resolve().parents[1]


async def main(doc: Path) -> int:
    load_dotenv(ROOT / ".env")
    text = extract_text(doc.name, doc.read_bytes())
    print(f"extracted {len(text)} characters from {doc.name}")
    client = RocketRideClient()
    await client.connect()
    token = None
    try:
        token = (await client.use(filepath=str(ROOT / "bid_factory.pipe")))["token"]
        print("task started")
        result = await asyncio.wait_for(
            client.send(token, build_pipeline_payload(text), objinfo={"name": f"{doc.name}.txt"}, mimetype="text/plain"),
            timeout=180,
        )
        extraction = StructuredAIRequirementExtractor().extract_ai({"data": result})
        print(f"{len(extraction.requirements)} requirements extracted:")
        for requirement in extraction.requirements:
            print(f" - {requirement.requirement_text}")
        return 0 if extraction.requirements else 1
    finally:
        if token:
            try:
                await client.terminate(token)
            except Exception:
                pass
        await client.disconnect()


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "real_rfp.pdf"
    sys.exit(asyncio.run(main(target)))
