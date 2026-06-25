from agentsave_dashboard.config import get_settings, Settings


def test_settings_has_required_fields():
    s = Settings()
    assert isinstance(s.stripe_api_key, str)
    assert isinstance(s.stripe_webhook_secret, str)
    assert isinstance(s.jwt_secret, str)
    assert isinstance(s.database_url, str)
    assert isinstance(s.cost_per_token_usd, float)


def test_settings_default_cost():
    s = Settings()
    assert s.cost_per_token_usd == 0.000003


def test_get_settings_returns_singleton():
    a = get_settings()
    b = get_settings()
    assert a is b
