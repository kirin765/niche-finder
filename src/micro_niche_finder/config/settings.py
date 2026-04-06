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

    google_custom_search_api_key: str | None = Field(default=None, alias="GOOGLE_CUSTOM_SEARCH_API_KEY")
    google_custom_search_cx: str | None = Field(default=None, alias="GOOGLE_CUSTOM_SEARCH_CX")
    google_custom_search_base_url: str = Field(
        default="https://customsearch.googleapis.com/customsearch/v1",
        alias="GOOGLE_CUSTOM_SEARCH_BASE_URL",
    )
    google_custom_search_daily_limit: int = Field(default=100, alias="GOOGLE_CUSTOM_SEARCH_DAILY_LIMIT")

    kosis_api_key: str | None = Field(default=None, alias="KOSIS_API_KEY")
    kosis_base_url: str = Field(
        default="https://kosis.kr/openapi/Param/statisticsParameterData.do",
        alias="KOSIS_BASE_URL",
    )
    kosis_org_id: str = Field(default="101", alias="KOSIS_ORG_ID")
    kosis_tbl_id: str | None = Field(default=None, alias="KOSIS_TBL_ID")
    kosis_employee_itm_id: str | None = Field(default=None, alias="KOSIS_EMPLOYEE_ITM_ID")
    kosis_prd_se: str = Field(default="Y", alias="KOSIS_PRD_SE")
    kosis_industry_dimension_key: str = Field(default="objL1", alias="KOSIS_INDUSTRY_DIMENSION_KEY")
    kosis_reference_year_offset: int = Field(default=1, alias="KOSIS_REFERENCE_YEAR_OFFSET")
    kosis_employee_daily_limit: int = Field(default=100, alias="KOSIS_EMPLOYEE_DAILY_LIMIT")
    kosis_employee_cadence_minutes: int = Field(default=1440, alias="KOSIS_EMPLOYEE_CADENCE_MINUTES")
    kosis_static_params_json: str | None = Field(default=None, alias="KOSIS_STATIC_PARAMS_JSON")
    kosis_industry_options_json: str | None = Field(default=None, alias="KOSIS_INDUSTRY_OPTIONS_JSON")

    naver_datalab_client_id: str | None = Field(default=None, alias="NAVER_DATALAB_CLIENT_ID")
    naver_datalab_client_secret: str | None = Field(default=None, alias="NAVER_DATALAB_CLIENT_SECRET")
    naver_datalab_base_url: str = Field(
        default="https://openapi.naver.com/v1/datalab/search",
        alias="NAVER_DATALAB_BASE_URL",
    )
    naver_datalab_daily_limit: int = Field(default=1000, alias="NAVER_DATALAB_DAILY_LIMIT")
    naver_search_client_id: str | None = Field(default=None, alias="NAVER_SEARCH_CLIENT_ID")
    naver_search_client_secret: str | None = Field(default=None, alias="NAVER_SEARCH_CLIENT_SECRET")
    naver_search_base_url: str = Field(
        default="https://openapi.naver.com/v1/search/webkr.json",
        alias="NAVER_SEARCH_BASE_URL",
    )
    naver_search_display: int = Field(default=5, alias="NAVER_SEARCH_DISPLAY")
    naver_search_daily_limit: int = Field(default=300, alias="NAVER_SEARCH_DAILY_LIMIT")
    naver_shopping_insight_base_url: str = Field(
        default="https://openapi.naver.com/v1/datalab/shopping/categories",
        alias="NAVER_SHOPPING_INSIGHT_BASE_URL",
    )
    naver_shopping_insight_daily_limit: int = Field(default=300, alias="NAVER_SHOPPING_INSIGHT_DAILY_LIMIT")
    naver_shopping_insight_cadence_minutes: int = Field(default=720, alias="NAVER_SHOPPING_INSIGHT_CADENCE_MINUTES")
    naver_shopping_category_options_json: str | None = Field(default=None, alias="NAVER_SHOPPING_CATEGORY_OPTIONS_JSON")
    collector_interval_minutes: int = Field(default=15, alias="COLLECTOR_INTERVAL_MINUTES")
    collector_schedule_cadence_minutes: int = Field(default=180, alias="COLLECTOR_SCHEDULE_CADENCE_MINUTES")
    collector_default_priority: int = Field(default=100, alias="COLLECTOR_DEFAULT_PRIORITY")
    top_candidate_analysis_count: int = Field(default=10, alias="TOP_CANDIDATE_ANALYSIS_COUNT")



@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
