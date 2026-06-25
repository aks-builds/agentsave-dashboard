import json
import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


async def _seed_user_with_stripe(db) -> tuple[str, str]:
    """Insert a user with a Stripe customer ID. Return (user_id, customer_id)."""
    user_id = str(uuid.uuid4())
    customer_id = "cus_test_abc123"
    now = datetime.now(timezone.utc).isoformat()

    await db.execute(
        "INSERT INTO users (id, email, stripe_customer_id, tier, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, "billing@example.com", customer_id, "free", now),
    )
    await db.commit()
    return user_id, customer_id


@pytest.mark.asyncio
async def test_handle_checkout_completed_upgrades_tier(db):
    from agentsave_dashboard.services.billing_service import handle_checkout_completed

    user_id, customer_id = await _seed_user_with_stripe(db)
    session = {
        "customer": customer_id,
        "metadata": {"tier": "pro"},
    }
    await handle_checkout_completed(session, db)

    cursor = await db.execute("SELECT tier FROM users WHERE id = ?", (user_id,))
    row = await cursor.fetchone()
    assert row["tier"] == "pro"


@pytest.mark.asyncio
async def test_handle_subscription_deleted_downgrades_to_free(db):
    from agentsave_dashboard.services.billing_service import handle_subscription_deleted

    user_id, customer_id = await _seed_user_with_stripe(db)
    await db.execute("UPDATE users SET tier = 'pro' WHERE id = ?", (user_id,))
    await db.commit()

    subscription = {"customer": customer_id}
    await handle_subscription_deleted(subscription, db)

    cursor = await db.execute("SELECT tier FROM users WHERE id = ?", (user_id,))
    row = await cursor.fetchone()
    assert row["tier"] == "free"


@pytest.mark.asyncio
async def test_billing_webhook_invalid_signature_returns_400(client, db):
    response = await client.post(
        "/api/billing/webhook",
        content=b'{"type": "checkout.session.completed"}',
        headers={
            "Content-Type": "application/json",
            "Stripe-Signature": "invalid_sig",
        },
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_billing_portal_no_auth_returns_401(client, db):
    response = await client.get("/api/billing/portal")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_portal_url_calls_stripe(db):
    from agentsave_dashboard.services.billing_service import get_portal_url

    mock_session = MagicMock()
    mock_session.url = "https://billing.stripe.com/session/test_abc"

    with patch(
        "agentsave_dashboard.services.billing_service.stripe.billing_portal.Session.create",
        return_value=mock_session,
    ):
        url = get_portal_url("cus_test_abc123", return_url="https://app.agentsave.io/billing")
    assert url == "https://billing.stripe.com/session/test_abc"
