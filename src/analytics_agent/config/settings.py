from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ANALYTICS_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    port: int = Field(default=8001)
    database_url: str = Field(default="sqlite:///./analytics.db")

    # LLM (OpenRouter) — optional in Phase 1
    openrouter_api_key: str = Field(default="")
    llm_model: str = Field(default="anthropic/claude-sonnet-4-6")

    # Connector keys — optional in Phase 1; each lights up its connector when set
    ga4_property_id: str = Field(default="")
    ga4_credentials_json: str = Field(default="")
    business_db_url: str = Field(default="")
    play_store_credentials_json: str = Field(default="")
    appstore_connect_key_id: str = Field(default="")
    appstore_connect_issuer_id: str = Field(default="")
    appstore_connect_private_key_p8: str = Field(default="")
    instagram_access_token: str = Field(default="")
    linkedin_access_token: str = Field(default="")
    facebook_access_token: str = Field(default="")

    log_level: str = Field(default="INFO")

    @property
    def resolved_llm_provider(self) -> str:
        """`auto` → real when the OpenRouter key is set, else `sample`."""
        return "openrouter" if self.openrouter_api_key else "sample"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
