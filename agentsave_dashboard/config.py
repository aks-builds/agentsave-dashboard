from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    stripe_api_key: str = "sk_test_placeholder"
    stripe_webhook_secret: str = "whsec_placeholder"
    jwt_secret: str = "dev_secret_key_replace_in_production_32ch"
    database_url: str = "agentsave.db"
    cost_per_token_usd: float = 0.000003

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
