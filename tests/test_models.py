from datetime import datetime, timezone
from agentsave_dashboard.models import (
    EventPayload,
    MetricsResponse,
    TokenCreateRequest,
    TokenResponse,
    UserTier,
)


def test_event_payload_valid():
    data = {
        "run_id": "abc-123",
        "framework": "langchain",
        "model_name": "gpt-4o",
        "tokens_before": 12400,
        "tokens_after": 8650,
        "iterations_total": 8,
        "iterations_saved": 0,
        "task_success": True,
        "timestamp": "2026-06-23T10:00:00Z",
    }
    ep = EventPayload(**data)
    assert ep.run_id == "abc-123"
    assert ep.tokens_before == 12400
    assert ep.task_success is True


def test_event_payload_rejects_negative_tokens():
    import pytest
    with pytest.raises(Exception):
        EventPayload(
            run_id="x",
            framework="langchain",
            model_name="gpt-4o",
            tokens_before=-1,
            tokens_after=100,
            iterations_total=1,
            iterations_saved=0,
            task_success=True,
            timestamp="2026-06-23T10:00:00Z",
        )


def test_metrics_response_fields():
    m = MetricsResponse(
        project_id="proj-1",
        period="7d",
        tokens_saved=3750,
        cost_saved_usd=0.01125,
        success_rate=0.95,
        event_count=10,
    )
    assert m.cost_saved_usd == 0.01125


def test_token_create_request():
    req = TokenCreateRequest(name="my-token", project_id="proj-1")
    assert req.name == "my-token"


def test_token_response_fields():
    tr = TokenResponse(
        id="tok-1",
        name="my-token",
        project_id="proj-1",
        created_at="2026-06-23T10:00:00Z",
        last_used_at=None,
    )
    assert tr.last_used_at is None


def test_user_tier_literals():
    assert UserTier.__args__ == ("free", "pro", "enterprise")
