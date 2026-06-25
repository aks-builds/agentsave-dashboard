from dataclasses import dataclass, field
from pathlib import Path

import jwt
from jwt.exceptions import InvalidTokenError

_PUBLIC_KEY_PATH = Path(__file__).parent / "keys" / "public.pem"

FEATURES_BY_TIER: dict[str, dict] = {
    "free": {
        "history_days": 7,
        "unlimited_projects": False,
        "webhook_alerts": False,
        "csv_export": False,
        "sso_saml": False,
        "audit_logs": False,
        "inferroute": False,
    },
    "pro": {
        "history_days": 90,
        "unlimited_projects": True,
        "webhook_alerts": True,
        "csv_export": True,
        "sso_saml": False,
        "audit_logs": False,
        "inferroute": False,
    },
    "enterprise": {
        "history_days": 365,
        "unlimited_projects": True,
        "webhook_alerts": True,
        "csv_export": True,
        "sso_saml": True,
        "audit_logs": True,
        "inferroute": True,
    },
}


@dataclass
class TierInfo:
    tier: str
    org: str
    seats_allowed: int
    expires_at: str | None
    features: dict = field(default_factory=dict)
    expired: bool = False

    @classmethod
    def free(cls, expired: bool = False) -> "TierInfo":
        return cls(
            tier="free",
            org="",
            seats_allowed=1,
            expires_at=None,
            features=dict(FEATURES_BY_TIER["free"]),
            expired=expired,
        )


def _load_public_key() -> str:
    return _PUBLIC_KEY_PATH.read_text()


async def resolve_tier(db) -> TierInfo:
    cursor = await db.execute(
        "SELECT value FROM config WHERE key = 'license_key'"
    )
    row = await cursor.fetchone()
    if not row:
        return TierInfo.free()

    token = row[0]
    try:
        public_key = _load_public_key()
        payload = jwt.decode(token, public_key, algorithms=["RS256"], issuer="agentsave")
    except jwt.ExpiredSignatureError:
        return TierInfo.free(expired=True)
    except InvalidTokenError:
        return TierInfo.free()

    tier = payload.get("tier", "free")
    if tier not in FEATURES_BY_TIER:
        tier = "free"

    from datetime import datetime, timezone
    exp_ts = payload.get("exp")
    expires_at = (
        datetime.fromtimestamp(exp_ts, tz=timezone.utc).date().isoformat()
        if exp_ts else None
    )

    return TierInfo(
        tier=tier,
        org=payload.get("org", ""),
        seats_allowed=payload.get("seats", 1),
        expires_at=expires_at,
        features=dict(FEATURES_BY_TIER[tier]),
        expired=False,
    )
