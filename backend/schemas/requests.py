from pydantic import BaseModel, Field


class ReviewRequest(BaseModel):
    decision: str = Field(min_length=1, max_length=100)
    comment: str | None = Field(default=None, max_length=5000)
    reviewer: str | None = Field(default=None, max_length=255)