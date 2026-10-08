from datetime import datetime
from uuid import UUID
from typing import Any

from pydantic import BaseModel

from backend.models.entities import Bid


class UploadResponse(BaseModel):
    bid_id: UUID
    filename: str
    file_type: str
    upload_timestamp: datetime
    processing_status: str
    bid: Bid
    message: str = "RFP uploaded successfully."


class AnalysisResponse(BaseModel):
    bid_id: UUID
    status: str
    message: str
    data: dict[str, Any] | None = None


class GenerateResponse(BaseModel):
    bid_id: UUID
    status: str
    message: str
    data: dict[str, Any] | None = None