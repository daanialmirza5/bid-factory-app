import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.api import routes
from backend.main import app
from backend.models.entities import Bid, RFP
from backend.schemas.orchestration import BidAnalysisResult
from backend.services.rocketride_service import AI_UNAVAILABLE, RocketRideService, RocketRideServiceError
from backend.utils.config import get_settings


def make_bid(filename: str = "rfp.pdf", content_type: str = "application/pdf") -> Bid:
    bid_id = uuid4()
    return Bid(
        id=bid_id,
        bid_id=bid_id,
        rfp=RFP(filename=filename, title="RFP", file_type="pdf", file_size=10, content_type=content_type),
    )


class FailingPipelineService(RocketRideService):
    def __init__(self) -> None:
        super().__init__()
        self.direct_calls = 0

    async def _run_pipeline(self, bid, document):
        raise ConnectionError("pipeline down secret-value")

    async def _direct_extraction(self, bid, document):
        self.direct_calls += 1
        return {"status": "completed", "data": {"text": "The vendor must do X."}}


@pytest.fixture
def fallback(monkeypatch):
    def set_flag(enabled: bool) -> None:
        monkeypatch.setattr(get_settings(), "ai_fallback_direct_groq", enabled)
    return set_flag


def test_pipeline_failure_raises_when_fallback_disabled(fallback) -> None:
    fallback(False)
    service = FailingPipelineService()

    with pytest.raises(RocketRideServiceError) as exc_info:
        asyncio.run(service.analyze(make_bid(), b"doc"))

    assert str(exc_info.value) == AI_UNAVAILABLE
    assert "secret-value" not in str(exc_info.value)
    assert service.direct_calls == 0


def test_pipeline_failure_uses_direct_route_only_when_enabled(fallback) -> None:
    fallback(True)
    service = FailingPipelineService()

    result = asyncio.run(service.analyze(make_bid(), b"doc"))

    assert service.direct_calls == 1
    assert result["data"]["text"] == "The vendor must do X."


def test_direct_extraction_without_key_raises_instead_of_fabricating(monkeypatch) -> None:
    monkeypatch.delenv("ROCKETRIDE_GROQ_KEY", raising=False)

    with pytest.raises(RocketRideServiceError) as exc_info:
        asyncio.run(RocketRideService()._direct_extraction(make_bid(), b"doc"))

    assert str(exc_info.value) == AI_UNAVAILABLE


def test_direct_extraction_llm_error_raises_instead_of_fabricating(monkeypatch) -> None:
    import groq

    class BrokenGroq:
        def __init__(self, api_key):
            self.chat = self
            self.completions = self

        def create(self, **kwargs):
            raise RuntimeError("401 Invalid API Key")

    monkeypatch.setenv("ROCKETRIDE_GROQ_KEY", "test-placeholder")
    monkeypatch.setattr(groq, "Groq", BrokenGroq)
    from backend.services.document_ingestion import DocumentIngestionService
    monkeypatch.setattr(DocumentIngestionService, "_extract_docx", staticmethod(lambda _: [{"text": "RFP text"}]))

    with pytest.raises(RocketRideServiceError) as exc_info:
        asyncio.run(RocketRideService()._direct_extraction(make_bid("rfp.docx", "application/octet-stream"), b"doc"))

    assert str(exc_info.value) == AI_UNAVAILABLE


def test_missing_rocketride_connection_is_reported(monkeypatch) -> None:
    monkeypatch.delenv("ROCKETRIDE_URI", raising=False)
    monkeypatch.delenv("ROCKETRIDE_APIKEY", raising=False)

    with pytest.raises(RocketRideServiceError, match="not configured"):
        asyncio.run(RocketRideService()._run_pipeline(make_bid(), b"doc"))


def test_failed_analysis_returns_503() -> None:
    class FailingOrchestrator:
        async def analyze(self, bid: Bid, document: bytes) -> BidAnalysisResult:
            return BidAnalysisResult(bid_id=bid.bid_id, processing_status="failed", errors=["RocketRide pipeline execution failed."])

    original = routes.bid_analysis_orchestrator
    routes.bid_analysis_orchestrator = FailingOrchestrator()
    try:
        client = TestClient(app)
        upload = client.post("/api/bids/upload", files={"file": ("rfp.pdf", b"%PDF-1.7 test", "application/pdf")})
        response = client.post(f"/api/bids/{upload.json()['bid_id']}/analyze")
        assert response.status_code == 503, response.text
        assert response.json()["processing_status"] == "failed"
        assert response.json()["requirements"] == []
        assert response.json()["errors"] == ["RocketRide pipeline execution failed."]
    finally:
        routes.bid_analysis_orchestrator = original
