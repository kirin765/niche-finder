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

    brave_search_api_key: str | None = Field(default=None, alias="BRAVE_SEARCH_API_KEY")
    brave_search_base_url: str = Field(
        default="https://api.search.brave.com/res/v1/web/search",
        alias="BRAVE_SEARCH_BASE_URL",
    )
    brave_search_daily_limit: int = Field(default=100, alias="BRAVE_SEARCH_DAILY_LIMIT")

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
    kosis_profile_options_json: str | None = Field(default=None, alias="KOSIS_PROFILE_OPTIONS_JSON")

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
    naver_ads_customer_id: str | None = Field(default=None, alias="NAVER_ADS_CUSTOMER_ID")
    naver_ads_api_key: str | None = Field(default=None, alias="NAVER_ADS_API_KEY")
    naver_ads_secret_key: str | None = Field(default=None, alias="NAVER_ADS_SECRET_KEY")
    naver_ads_base_url: str = Field(default="https://api.naver.com/keywordstool", alias="NAVER_ADS_BASE_URL")
    naver_ads_daily_limit: int = Field(default=300, alias="NAVER_ADS_DAILY_LIMIT")
    naver_search_display: int = Field(default=5, alias="NAVER_SEARCH_DISPLAY")
    naver_search_daily_limit: int = Field(default=300, alias="NAVER_SEARCH_DAILY_LIMIT")
    search_weight_google_demand: float = Field(default=0.55, alias="SEARCH_WEIGHT_GOOGLE_DEMAND")
    search_weight_naver_demand: float = Field(default=0.45, alias="SEARCH_WEIGHT_NAVER_DEMAND")
    search_weight_google_gtm: float = Field(default=0.35, alias="SEARCH_WEIGHT_GOOGLE_GTM")
    search_weight_naver_gtm: float = Field(default=0.65, alias="SEARCH_WEIGHT_NAVER_GTM")
    naver_shopping_insight_base_url: str = Field(
        default="https://openapi.naver.com/v1/datalab/shopping/categories",
        alias="NAVER_SHOPPING_INSIGHT_BASE_URL",
    )
    naver_shopping_insight_daily_limit: int = Field(default=300, alias="NAVER_SHOPPING_INSIGHT_DAILY_LIMIT")
    naver_shopping_insight_cadence_minutes: int = Field(default=720, alias="NAVER_SHOPPING_INSIGHT_CADENCE_MINUTES")
    naver_shopping_category_options_json: str | None = Field(default=None, alias="NAVER_SHOPPING_CATEGORY_OPTIONS_JSON")
    telegram_bot_token: str | None = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str | None = Field(default=None, alias="TELEGRAM_CHAT_ID")
    telegram_base_url: str = Field(default="https://api.telegram.org", alias="TELEGRAM_BASE_URL")
    gmail_smtp_host: str = Field(default="smtp.gmail.com", alias="GMAIL_SMTP_HOST")
    gmail_smtp_port: int = Field(default=465, alias="GMAIL_SMTP_PORT")
    gmail_username: str | None = Field(default=None, alias="GMAIL_USERNAME")
    gmail_app_password: str | None = Field(default=None, alias="GMAIL_APP_PASSWORD")
    gmail_from_email: str | None = Field(default=None, alias="GMAIL_FROM_EMAIL")
    gmail_to_emails: str | None = Field(default=None, alias="GMAIL_TO_EMAILS")
    daily_report_timezone: str = Field(default="Asia/Seoul", alias="DAILY_REPORT_TIMEZONE")
    daily_report_hour: int = Field(default=9, alias="DAILY_REPORT_HOUR")
    daily_report_minute: int = Field(default=0, alias="DAILY_REPORT_MINUTE")
    daily_report_seed_limit: int = Field(default=5, alias="DAILY_REPORT_SEED_LIMIT")
    daily_report_candidate_count: int = Field(default=5, alias="DAILY_REPORT_CANDIDATE_COUNT")
    daily_report_top_k_per_seed: int = Field(default=1, alias="DAILY_REPORT_TOP_K_PER_SEED")
    daily_report_refresh_seeds: bool = Field(default=False, alias="DAILY_REPORT_REFRESH_SEEDS")
    collector_interval_minutes: int = Field(default=15, alias="COLLECTOR_INTERVAL_MINUTES")
    collector_schedule_cadence_minutes: int = Field(default=180, alias="COLLECTOR_SCHEDULE_CADENCE_MINUTES")
    collector_default_priority: int = Field(default=100, alias="COLLECTOR_DEFAULT_PRIORITY")
    top_candidate_analysis_count: int = Field(default=10, alias="TOP_CANDIDATE_ANALYSIS_COUNT")



@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
