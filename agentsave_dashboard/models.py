from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator

UserTier = Literal["free", "pro", "enterprise"]


class EventPayload(BaseModel):
    run_id: str
    framework: str
    model_name: str
    tokens_before: int = Field(ge=0)
    tokens_after: int = Field(ge=0)
    iterations_total: int = Field(ge=0)
    iterations_saved: int = Field(ge=0, default=0)
    task_success: bool
    timestamp: str  # ISO8601 UTC string from SDK


class MetricsResponse(BaseModel):
    project_id: str
    period: str
    tokens_saved: int
    cost_saved_usd: float
    success_rate: float
    event_count: int


class TokenCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    project_id: str


class TokenResponse(BaseModel):
    id: str
    name: str
    project_id: Optional[str]
    created_at: str
    last_used_at: Optional[str]


class UserResponse(BaseModel):
    id: str
    email: str
    tier: UserTier
    created_at: str


class BillingPortalResponse(BaseModel):
    url: str
