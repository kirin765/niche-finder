from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="Micro Niche Finder", alias="APP_NAME")
    app_env: str = Field(default="local", alias="APP_ENV")
    app_debug: bool = Field(default=False, alias="APP_DEBUG")
    database_url: str = Field(default="sqlite:///./micro_niche_finder.db", alias="DATABASE_URL")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: str | None = Field(default=None, alias="OPENAI_BASE_URL")
    openai_candidate_model: str = Field(default="gpt-5.4-mini", alias="OPENAI_CANDIDATE_MODEL")
    openai_final_model: str = Field(default="gpt-5.4", alias="OPENAI_FINAL_MODEL")
    openai_reasoning_effort: str = Field(default="medium", alias="OPENAI_REASONING_EFFORT")
    openai_text_verbosity: str = Field(default="medium", alias="OPENAI_TEXT_VERBOSITY")

    naver_datalab_client_id: str | None = Field(default=None, alias="NAVER_DATALAB_CLIENT_ID")
    naver_datalab_client_secret: str | None = Field(default=None, alias="NAVER_DATALAB_CLIENT_SECRET")
    naver_datalab_base_url: str = Field(
        default="https://openapi.naver.com/v1/datalab/search",
        alias="NAVER_DATALAB_BASE_URL",
    )
    naver_datalab_daily_limit: int = Field(default=1000, alias="NAVER_DATALAB_DAILY_LIMIT")
    collector_interval_minutes: int = Field(default=15, alias="COLLECTOR_INTERVAL_MINUTES")
    collector_schedule_cadence_minutes: int = Field(default=180, alias="COLLECTOR_SCHEDULE_CADENCE_MINUTES")
    collector_default_priority: int = Field(default=100, alias="COLLECTOR_DEFAULT_PRIORITY")
    top_candidate_analysis_count: int = Field(default=10, alias="TOP_CANDIDATE_ANALYSIS_COUNT")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
