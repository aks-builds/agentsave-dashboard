from __future__ import annotations

import stripe
import aiosqlite

from agentsave_dashboard.config import get_settings


def _configure_stripe() -> None:
    stripe.api_key = get_settings().stripe_api_key


async def handle_checkout_completed(
    session: dict,
    db: aiosqlite.Connection,
) -> None:
    """Upgrade user tier when a Stripe checkout.session.completed fires."""
    customer_id = session.get("customer")
    tier = session.get("metadata", {}).get("tier", "pro")
    if customer_id:
        await db.execute(
            "UPDATE users SET tier = ? WHERE stripe_customer_id = ?",
            (tier, customer_id),
        )
        await db.commit()


async def handle_subscription_deleted(
    subscription: dict,
    db: aiosqlite.Connection,
) -> None:
    """Downgrade user to free when a subscription is cancelled."""
    customer_id = subscription.get("customer")
    if customer_id:
        await db.execute(
            "UPDATE users SET tier = 'free' WHERE stripe_customer_id = ?",
            (customer_id,),
        )
        await db.commit()


def get_portal_url(customer_id: str, return_url: str = "https://app.agentsave.io/billing") -> str:
    """Create a Stripe billing portal session and return its URL."""
    _configure_stripe()
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )
    return session.url
