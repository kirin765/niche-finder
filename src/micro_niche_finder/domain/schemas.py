from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from micro_niche_finder.domain.enums import CandidateStatus, FitLevel, RepeatFrequency


class CreateSeedCategoryRequest(BaseModel):
    name: str
    description: str | None = None


class SeedCategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    created_at: datetime


class SeedCategorySuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str
    rationale: str


class SeedCategoryDiscoveryPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seeds: list[SeedCategorySuggestion]


class SeedCategoryDiscoveryResult(BaseModel):
    prompt_version: str = "seed_generation.v1"
    schema_version: str = "1.0"
    seeds: list[SeedCategorySuggestion]


class ProblemCandidateGenerated(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seed_category: str
    persona: str
    job_to_be_done: str
    pain: str
    repeat_frequency: RepeatFrequency
    current_workaround: list[str]
    software_fit: FitLevel
    payment_likelihood: FitLevel
    online_gtm_fit: FitLevel
    market_size_confidence: FitLevel
    risk_flags: list[str]
    query_candidates: list[str]
    online_demand_hypothesis: str
    online_acquisition_channels: list[str]


class CandidateGenerationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidates: list[ProblemCandidateGenerated]


class CandidateGenerationResult(BaseModel):
    prompt_version: str = "candidate_generation.v1"
    schema_version: str = "1.0"
    candidates: list[ProblemCandidateGenerated]


class QueryExpansionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seed_category: str
    persona: str
    canonical_name: str
    expanded_queries: list[str]
    commercial_queries: list[str]
    informational_queries: list[str]


class QueryGroupNormalized(BaseModel):
    canonical_name: str
    queries: list[str]
    excluded_queries: list[str] = Field(default_factory=list)
    overlap_score: float


class KeywordGroupRequest(BaseModel):
    groupName: str
    keywords: list[str]


class DataLabRequest(BaseModel):
    startDate: date
    endDate: date
    timeUnit: str
    keywordGroups: list[KeywordGroupRequest]
    device: str | None = None
    ages: list[str] | None = None
    gender: str | None = None


class DataLabResultPoint(BaseModel):
    period: date
    ratio: float


class DataLabResultGroup(BaseModel):
    title: str
    keywords: list[str]
    data: list[DataLabResultPoint]


class DataLabResponse(BaseModel):
    startDate: date
    endDate: date
    timeUnit: str
    results: list[DataLabResultGroup]


class TrendFeatureSet(BaseModel):
    recent_growth_4w: float
    recent_growth_12w: float
    moving_avg_ratio: float
    volatility: float
    spike_ratio: float
    decay_after_peak: float
    seasonality_score: float
    query_diversity: float
    problem_specificity: float
    commercial_intent_ratio: float
    brand_dependency_score: float
    online_demand_score: float
    absolute_demand_score: float
    payability_score: float
    market_size_sufficiency_score: float
    online_gtm_efficiency_score: float
    market_size_ceiling_score: float
    competitive_whitespace_score: float
    keyword_difficulty_score: float


class CollectionTarget(BaseModel):
    key: str
    weeks: int
    time_unit: str = "week"
    device: str | None = None
    ages: list[str] | None = None
    gender: str | None = None
    updates_features: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class CollectorRunSummary(BaseModel):
    source: str
    run_started_at: datetime
    allowance: int
    schedules_considered: int
    schedules_processed: int
    calls_made: int
    errors: list[str] = Field(default_factory=list)


class KosisIndustryOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    label: str
    description: str


class KosisIndustrySelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    label: str
    rationale: str


class KosisProfileOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    label: str
    kind: str
    tbl_id: str
    metrics: dict[str, str]
    static_params: dict[str, str] = Field(default_factory=dict)
    industry_dimension_key: str | None = None
    time_range: list[int] | None = None
    applies_to_prefixes: list[str] = Field(default_factory=list)
    exclude_prefixes: list[str] = Field(default_factory=list)


class KosisProfileRequest(BaseModel):
    profile_name: str
    profile_label: str
    profile_kind: str
    metric_key: str
    metric_item_id: str
    source_label: str
    source_table_id: str
    industry_code: str
    industry_label: str
    start_year: int
    end_year: int
    params: dict[str, str]


class KosisMetricPoint(BaseModel):
    period: str
    value: float


class KosisProfileResponse(BaseModel):
    profile_name: str
    profile_label: str
    profile_kind: str
    metric_key: str
    source_label: str
    source_table_id: str
    industry_code: str
    industry_label: str
    start_year: int
    end_year: int
    latest_value: float | None
    cagr: float | None = None
    regional_concentration: float | None = None
    series: list[KosisMetricPoint] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)


class KosisEmployeeRequest(BaseModel):
    industry_code: str
    industry_label: str
    reference_year: int
    params: dict[str, str]


class KosisEmployeeResponse(BaseModel):
    industry_code: str
    industry_label: str
    reference_year: int
    employee_count: int | None
    source_label: str
    source_table_id: str
    rows: list[dict[str, Any]] = Field(default_factory=list)


class MarketSizeContext(BaseModel):
    source: str
    source_label: str
    industry_code: str
    industry_label: str
    reference_year: int
    employee_count: int | None
    business_count: int | None = None
    revenue: float | None = None
    value_added: float | None = None
    revenue_per_employee: float | None = None
    employee_cagr: float | None = None
    business_cagr: float | None = None
    regional_concentration: float | None = None
    profile_summaries: list[str] = Field(default_factory=list)
    summary: str
    rationale: str


class SearchEvidenceContext(BaseModel):
    source: str
    source_label: str
    query: str
    total_results: int | None
    top_titles: list[str] = Field(default_factory=list)
    summary: str


class KeywordVolumeRequest(BaseModel):
    keywords: list[str]


class KeywordVolumeMetric(BaseModel):
    keyword: str
    monthly_pc_searches: int | None = None
    monthly_mobile_searches: int | None = None
    monthly_total_searches: int | None = None
    competition_index: str | None = None


class AbsoluteDemandContext(BaseModel):
    source: str
    source_label: str
    keywords: list[str]
    max_monthly_searches: int | None = None
    average_monthly_searches: int | None = None
    keyword_metrics: list[KeywordVolumeMetric] = Field(default_factory=list)
    summary: str


class OnlineGTMContext(BaseModel):
    query: str
    channel_signals: list[str] = Field(default_factory=list)
    channel_counts: dict[str, int] = Field(default_factory=dict)
    competitor_domains: list[str] = Field(default_factory=list)
    community_presence_score: float | None = None
    seo_discoverability_score: float | None = None
    competitor_presence_score: float | None = None
    brand_concentration_score: float | None = None
    competitive_whitespace_score: float | None = None
    summary: str


class PricingEvidenceContext(BaseModel):
    source: str
    source_label: str
    search_queries: list[str]
    pricing_page_count: int
    detected_price_points_krw: list[int] = Field(default_factory=list)
    median_monthly_price_krw: int | None = None
    max_monthly_price_krw: int | None = None
    summary: str


class ShoppingEvidenceContext(BaseModel):
    source: str
    source_label: str
    category_code: str
    category_label: str
    reference_window: str
    recent_ratio: float | None
    peak_ratio: float | None
    summary: str


class PublicDataRecommendation(BaseModel):
    dataset_id: str
    source_label: str
    dataset_name: str
    dataset_url: str
    relevance: str
    use_case: str
    caveat: str


class PublicDataContext(BaseModel):
    summary: str
    recommendations: list[PublicDataRecommendation] = Field(default_factory=list)


class NaverShoppingCategoryOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    label: str
    description: str


class NaverShoppingCategorySelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    label: str
    rationale: str


class NaverShoppingCategoryRequest(BaseModel):
    name: str
    param: list[str]


class NaverShoppingInsightRequest(BaseModel):
    startDate: date
    endDate: date
    timeUnit: str
    category: list[NaverShoppingCategoryRequest]
    device: str | None = None
    gender: str | None = None
    ages: list[str] | None = None


class NaverShoppingInsightPoint(BaseModel):
    period: date
    ratio: float


class NaverShoppingInsightResult(BaseModel):
    title: str
    category: list[str]
    data: list[NaverShoppingInsightPoint]


class NaverShoppingInsightResponse(BaseModel):
    startDate: date
    endDate: date
    timeUnit: str
    results: list[NaverShoppingInsightResult]


class NaverSearchRequest(BaseModel):
    query: str
    display: int = 5
    start: int = 1
    sort: str = "sim"


class NaverSearchItem(BaseModel):
    title: str
    link: str | None = None
    description: str | None = None


class NaverSearchResponse(BaseModel):
    lastBuildDate: str | None = None
    total: int = 0
    start: int = 1
    display: int = 0
    items: list[NaverSearchItem] = Field(default_factory=list)


class GoogleSearchRequest(BaseModel):
    q: str
    num: int = 5
    gl: str = "kr"
    hl: str = "ko"
    safe: str = "off"


class GoogleSearchResultItem(BaseModel):
    title: str | None = None
    link: str | None = None
    snippet: str | None = None
    displayLink: str | None = None


class GoogleSearchInformation(BaseModel):
    totalResults: str = "0"


class GoogleCustomSearchResponse(BaseModel):
    searchInformation: GoogleSearchInformation
    items: list[GoogleSearchResultItem] = Field(default_factory=list)


class ScoreBreakdown(BaseModel):
    repeated_pain: float
    problem_intensity: float
    payment_likelihood: float
    online_demand: float
    market_size_sufficiency: float
    online_gtm_efficiency: float
    market_size_ceiling: float
    competitive_whitespace: float
    keyword_difficulty: float
    implementation_feasibility: float
    penalties: float
    final_score: float
    reasoning_summary: str


class FinalAnalysisInput(BaseModel):
    canonical_name: str
    persona: str
    problem_summary: str
    query_group: list[str]
    features: TrendFeatureSet
    score_breakdown: ScoreBreakdown
    risk_flags: list[str]
    market_size_context: MarketSizeContext | None = None
    search_evidence_context: SearchEvidenceContext | None = None
    absolute_demand_context: AbsoluteDemandContext | None = None
    shopping_evidence_context: ShoppingEvidenceContext | None = None
    public_data_context: PublicDataContext | None = None
    online_gtm_context: OnlineGTMContext | None = None
    pricing_evidence_context: PricingEvidenceContext | None = None


class FinalAnalysisOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    niche_name: str
    persona: str
    problem_summary: str
    saas_fit_score: int
    trend_signal_score: int
    payment_likelihood: str
    implementation_feasibility: str
    mvp_idea: list[str]
    go_to_market: list[str]
    online_demand_summary: str
    market_size_summary: str
    market_size_sufficiency_summary: str
    search_evidence_summary: str
    shopping_evidence_summary: str
    public_data_summary: str
    online_gtm_summary: str
    recommended_online_channels: list[str]
    risk_flags: list[str]
    recommended_priority: int


class PipelineRunRequest(BaseModel):
    seed_category_id: int
    candidate_count: int = Field(default=20, ge=5, le=50)
    top_k: int = Field(default=10, ge=1, le=30)


class PipelineRunResponse(BaseModel):
    seed_category_id: int
    generated_candidates: int
    scored_candidates: int
    reported_candidates: int
    reports: list[FinalAnalysisOutput]


class FinalReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    problem_candidate_id: int
    recommended_priority: int
    report_json: dict[str, Any]
    created_at: datetime
