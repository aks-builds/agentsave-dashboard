from __future__ import annotations

import json
from typing import Annotated

import aiosqlite
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status

from agentsave_dashboard.auth import require_jwt
from agentsave_dashboard.config import get_settings
from agentsave_dashboard.database import get_db
from agentsave_dashboard.models import BillingPortalResponse
from agentsave_dashboard.services.billing_service import (
    get_portal_url,
    handle_checkout_completed,
    handle_subscription_deleted,
)

router = APIRouter()


@router.post("/api/billing/webhook", status_code=200)
async def billing_webhook(
    request: Request,
    db: Annotated[aiosqlite.Connection, Depends(get_db)],
) -> dict:
    settings = get_settings()
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except (stripe.error.SignatureVerificationError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature",
        ) from exc

    if event["type"] == "checkout.session.completed":
        await handle_checkout_completed(event["data"]["object"], db)
    elif event["type"] == "customer.subscription.deleted":
        await handle_subscription_deleted(event["data"]["object"], db)

    return {"received": True}


@router.get("/api/billing/portal", response_model=BillingPortalResponse)
async def billing_portal(
    db: Annotated[aiosqlite.Connection, Depends(get_db)],
    jwt_payload: Annotated[dict, Depends(require_jwt)],
) -> BillingPortalResponse:
    user_id = jwt_payload["sub"]
    cursor = await db.execute(
        "SELECT stripe_customer_id FROM users WHERE id = ?", (user_id,)
    )
    row = await cursor.fetchone()
    if row is None or row["stripe_customer_id"] is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Stripe customer found for this user",
        )
    url = get_portal_url(row["stripe_customer_id"])
    return BillingPortalResponse(url=url)
