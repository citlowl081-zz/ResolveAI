"""Logistics request/response schemas."""

from pydantic import BaseModel, Field


class LogisticsEventRequest(BaseModel):
    status: str
    location: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=500)


class LogisticsEventResponse(BaseModel):
    timestamp: str
    status: str
    location: str
    description: str


class LogisticsResponse(BaseModel):
    id: str
    order_id: str
    tracking_number: str
    carrier: str
    status: str
    current_location: str | None = None
    estimated_delivery: str | None = None
    actual_delivery: str | None = None
    events: list[dict] = Field(default_factory=list)
