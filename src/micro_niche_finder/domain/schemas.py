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
    risk_flags: list[str]
    query_candidates: list[str]


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
    age_concentration: float
    gender_concentration: float
    mobile_ratio: float
    segment_consistency: float
    query_diversity: float
    problem_specificity: float
    commercial_intent_ratio: float
    brand_dependency_score: float


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
    persistent_signal: float
    segment_focus: float
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
