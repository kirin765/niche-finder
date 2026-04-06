from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from micro_niche_finder.domain.enums import CandidateStatus
from micro_niche_finder.domain.schemas import (
    FinalAnalysisInput,
    GoogleSearchRequest,
    MarketSizeContext,
    NaverSearchRequest,
    OnlineGTMContext,
    PipelineRunResponse,
    PublicDataContext,
    ShoppingEvidenceContext,
)
from micro_niche_finder.jobs import build_reports, collect_trends, compute_features, generate_candidates, score_candidates
from micro_niche_finder.repos.collection_repo import CollectionRepository
from micro_niche_finder.repos.candidate_repo import CandidateRepository, QueryGroupRepository, SeedCategoryRepository
from micro_niche_finder.repos.score_repo import ScoreRepository
from micro_niche_finder.repos.trend_repo import TrendRepository
from micro_niche_finder.services.collection_scheduler_service import CollectionSchedulerService
from micro_niche_finder.services.clustering_service import QueryClusteringService
from micro_niche_finder.services.datalab_service import NaverDataLabService
from micro_niche_finder.services.feature_service import FeatureExtractionService
from micro_niche_finder.services.google_search_service import GoogleSearchService
from micro_niche_finder.services.kosis_employee_service import KosisEmployeeService
from micro_niche_finder.services.llm_service import OpenAIResearchService
from micro_niche_finder.services.naver_search_service import NaverSearchService
from micro_niche_finder.services.naver_shopping_insight_service import NaverShoppingInsightService
from micro_niche_finder.services.public_data_opportunity_service import PublicDataOpportunityService
from micro_niche_finder.services.report_service import ReportService
from micro_niche_finder.services.scoring_service import ScoringService


class PipelineService:
    def __init__(
        self,
        *,
        llm_service: OpenAIResearchService,
        datalab_service: NaverDataLabService,
        kosis_employee_service: KosisEmployeeService,
        google_search_service: GoogleSearchService,
        naver_search_service: NaverSearchService,
        naver_shopping_insight_service: NaverShoppingInsightService,
        public_data_opportunity_service: PublicDataOpportunityService,
        clustering_service: QueryClusteringService,
        feature_service: FeatureExtractionService,
        collection_scheduler_service: CollectionSchedulerService,
        scoring_service: ScoringService,
        report_service: ReportService,
    ) -> None:
        self.llm_service = llm_service
        self.datalab_service = datalab_service
        self.kosis_employee_service = kosis_employee_service
        self.google_search_service = google_search_service
        self.naver_search_service = naver_search_service
        self.naver_shopping_insight_service = naver_shopping_insight_service
        self.public_data_opportunity_service = public_data_opportunity_service
        self.clustering_service = clustering_service
        self.feature_service = feature_service
        self.collection_scheduler_service = collection_scheduler_service
        self.scoring_service = scoring_service
        self.report_service = report_service

    def run(
        self,
        *,
        session: Session,
        seed_category_id: int,
        candidate_count: int,
        top_k: int,
    ) -> PipelineRunResponse:
        seed_repo = SeedCategoryRepository(session)
        candidate_repo = CandidateRepository(session)
        query_repo = QueryGroupRepository(session)
        collection_repo = CollectionRepository(session)
        trend_repo = TrendRepository(session)
        score_repo = ScoreRepository(session)

        seed = seed_repo.get(seed_category_id)
        if seed is None:
            raise ValueError(f"Seed category {seed_category_id} not found")

        generated = generate_candidates.run(seed.name, candidate_count, self.llm_service)
        expansions = [self.llm_service.expand_queries(candidate) for candidate in generated.candidates]
        clustered = self.clustering_service.cluster_candidates(expansions)
        kosis_options = self.kosis_employee_service.industry_options() if self.kosis_employee_service.is_configured() else []
        shopping_options = (
            self.naver_shopping_insight_service.category_options()
            if self.naver_shopping_insight_service.is_configured()
            else []
        )

        scored_payloads: list[tuple[float, int, FinalAnalysisInput]] = []
        for index, candidate in enumerate(generated.candidates):
            candidate_entity = candidate_repo.create(
                seed_category_id=seed.id,
                persona=candidate.persona,
                job_to_be_done=candidate.job_to_be_done,
                pain=candidate.pain,
                repeat_frequency=candidate.repeat_frequency.value,
                current_workaround_json=candidate.current_workaround,
                software_fit=candidate.software_fit.value,
                payment_likelihood=candidate.payment_likelihood.value,
                risk_flags_json=candidate.risk_flags,
                status=CandidateStatus.GENERATED.value,
                prompt_version=generated.prompt_version,
                schema_version=generated.schema_version,
            )
            group = clustered[index]
            query_entity = query_repo.create(
                problem_candidate_id=candidate_entity.id,
                canonical_name=group.canonical_name,
                queries_json=group.queries,
                excluded_queries_json=group.excluded_queries,
                overlap_score=group.overlap_score,
            )
            collection_repo.upsert_schedule(
                query_group_id=query_entity.id,
                source="naver_datalab",
                priority=self.collection_scheduler_service.settings.collector_default_priority,
                cadence_minutes=self.collection_scheduler_service.settings.collector_schedule_cadence_minutes,
                collection_targets_json=[
                    target.model_dump(mode="json") for target in self.collection_scheduler_service.default_targets()
                ],
                next_collect_at=self.collection_scheduler_service.default_next_collect_at(),
            )
            collection_repo.upsert_schedule(
                query_group_id=query_entity.id,
                source=GoogleSearchService.SOURCE,
                priority=max(1, self.collection_scheduler_service.settings.collector_default_priority - 20),
                cadence_minutes=self.collection_scheduler_service.settings.collector_schedule_cadence_minutes,
                collection_targets_json=[
                    target.model_dump(mode="json")
                    for target in self.collection_scheduler_service.google_default_targets(len(group.queries))
                ],
                next_collect_at=self.collection_scheduler_service.default_next_collect_at(),
            )
            collection_repo.upsert_schedule(
                query_group_id=query_entity.id,
                source=NaverSearchService.SOURCE,
                priority=max(1, self.collection_scheduler_service.settings.collector_default_priority - 15),
                cadence_minutes=self.collection_scheduler_service.settings.collector_schedule_cadence_minutes,
                collection_targets_json=[
                    target.model_dump(mode="json")
                    for target in self.collection_scheduler_service.naver_search_default_targets(len(group.queries))
                ],
                next_collect_at=self.collection_scheduler_service.default_next_collect_at(),
            )
            market_size_context: MarketSizeContext | None = None
            search_evidence_context = None
            shopping_evidence_context: ShoppingEvidenceContext | None = None
            online_gtm_context: OnlineGTMContext | None = None
            google_online_gtm_context: OnlineGTMContext | None = None
            public_data_context: PublicDataContext | None = self.public_data_opportunity_service.analyze(
                canonical_name=group.canonical_name,
                persona=candidate.persona,
                problem_summary=candidate.pain,
                query_group=group.queries,
                risk_flags=candidate.risk_flags,
            )
            if kosis_options:
                selection = self.llm_service.select_kosis_industry(
                    canonical_name=group.canonical_name,
                    persona=candidate.persona,
                    problem_summary=candidate.pain,
                    query_group=group.queries,
                    options=kosis_options,
                )
                kosis_requests = self.kosis_employee_service.build_requests(selection)
                if kosis_requests:
                    collection_repo.upsert_schedule(
                        query_group_id=query_entity.id,
                        source=KosisEmployeeService.SOURCE,
                        priority=max(1, self.collection_scheduler_service.settings.collector_default_priority - 10),
                        cadence_minutes=self.collection_scheduler_service.settings.kosis_employee_cadence_minutes,
                        collection_targets_json=[
                            target.model_dump(mode="json")
                            for target in self.collection_scheduler_service.kosis_default_targets(kosis_requests)
                        ],
                        next_collect_at=self.collection_scheduler_service.default_next_collect_at(),
                    )
                    try:
                        kosis_responses = []
                        for kosis_request in kosis_requests:
                            kosis_response = self.kosis_employee_service.fetch_profile(kosis_request)
                            trend_repo.create_snapshot(
                                query_group_id=query_entity.id,
                                source=KosisEmployeeService.SOURCE,
                                window_start=datetime(kosis_response.start_year, 1, 1, tzinfo=timezone.utc),
                                window_end=datetime(kosis_response.end_year, 12, 31, tzinfo=timezone.utc),
                                target_key=f"{kosis_request.profile_name}_{kosis_request.metric_key}_initial",
                                request_payload_json=kosis_request.model_dump(mode="json"),
                                raw_response_json=kosis_response.model_dump(mode="json"),
                            )
                            kosis_responses.append(kosis_response)
                        market_size_context = self.kosis_employee_service.build_market_context(
                            selection=selection,
                            responses=kosis_responses,
                            rationale=selection.rationale,
                        )
                    except Exception as exc:
                        market_size_context = MarketSizeContext(
                            source=KosisEmployeeService.SOURCE,
                            source_label=KosisEmployeeService.SOURCE_LABEL,
                            industry_code=selection.code,
                            industry_label=selection.label,
                            reference_year=max(2000, datetime.now(timezone.utc).year - self.kosis_employee_service.settings.kosis_reference_year_offset),
                            employee_count=None,
                            summary=f"KOSIS 프로필 조회에 실패했다: {exc}",
                            rationale=selection.rationale,
                        )

            try:
                if group.queries:
                    query = group.queries[0]
                    request = NaverSearchRequest(
                        query=query,
                        display=self.naver_search_service.settings.naver_search_display,
                    )
                    response = self.naver_search_service.fetch(request)
                    now = datetime.now(timezone.utc)
                    trend_repo.create_snapshot(
                        query_group_id=query_entity.id,
                        source=NaverSearchService.SOURCE,
                        window_start=now,
                        window_end=now,
                        target_key="naver_search_initial",
                        request_payload_json=request.model_dump(mode="json", exclude_none=True),
                        raw_response_json=response.model_dump(mode="json"),
                    )
                    search_evidence_context = self.naver_search_service.build_search_evidence(
                        query=query,
                        response=response,
                    )
                    online_gtm_context = self.naver_search_service.build_online_gtm_context(
                        query=query,
                        response=response,
                        suggested_channels=candidate.online_acquisition_channels,
                    )
            except Exception:
                search_evidence_context = None
                online_gtm_context = None

            try:
                if group.queries and self.google_search_service.is_configured():
                    query = group.queries[0]
                    google_request = GoogleSearchRequest(q=query, num=5)
                    google_response = self.google_search_service.fetch(google_request)
                    now = datetime.now(timezone.utc)
                    trend_repo.create_snapshot(
                        query_group_id=query_entity.id,
                        source=GoogleSearchService.SOURCE,
                        window_start=now,
                        window_end=now,
                        target_key="google_search_initial",
                        request_payload_json=google_request.model_dump(mode="json", exclude_none=True),
                        raw_response_json=google_response.model_dump(mode="json"),
                    )
                    google_online_gtm_context = self.google_search_service.build_online_gtm_context(
                        query=query,
                        response=google_response,
                        suggested_channels=candidate.online_acquisition_channels,
                    )
            except Exception:
                google_online_gtm_context = None

            try:
                is_commerce_relevant = bool(shopping_options) and self.naver_shopping_insight_service.is_relevant_niche(
                    canonical_name=group.canonical_name,
                    persona=candidate.persona,
                    problem_summary=candidate.pain,
                    query_group=group.queries,
                )
                if is_commerce_relevant:
                    selection = self.llm_service.select_naver_shopping_category(
                        canonical_name=group.canonical_name,
                        persona=candidate.persona,
                        problem_summary=candidate.pain,
                        query_group=group.queries,
                        options=shopping_options,
                    )
                    collection_repo.upsert_schedule(
                        query_group_id=query_entity.id,
                        source=NaverShoppingInsightService.SOURCE,
                        priority=max(1, self.collection_scheduler_service.settings.collector_default_priority - 12),
                        cadence_minutes=self.collection_scheduler_service.settings.naver_shopping_insight_cadence_minutes,
                        collection_targets_json=[
                            target.model_dump(mode="json")
                            for target in self.collection_scheduler_service.naver_shopping_default_targets(selection)
                        ],
                        next_collect_at=self.collection_scheduler_service.default_next_collect_at(),
                    )
                    shopping_request = self.naver_shopping_insight_service.build_request(selection)
                    shopping_response = self.naver_shopping_insight_service.fetch(shopping_request)
                    trend_repo.create_snapshot(
                        query_group_id=query_entity.id,
                        source=NaverShoppingInsightService.SOURCE,
                        window_start=datetime.combine(
                            shopping_response.startDate, datetime.min.time(), tzinfo=timezone.utc
                        ),
                        window_end=datetime.combine(
                            shopping_response.endDate, datetime.min.time(), tzinfo=timezone.utc
                        ),
                        target_key="naver_shopping_initial",
                        request_payload_json=shopping_request.model_dump(mode="json", exclude_none=True),
                        raw_response_json=shopping_response.model_dump(mode="json"),
                    )
                    shopping_evidence_context = self.naver_shopping_insight_service.build_shopping_evidence(
                        selection=selection,
                        response=shopping_response,
                    )
            except Exception:
                shopping_evidence_context = None

            initial_request = self.datalab_service.build_request(group_name=group.canonical_name, queries=group.queries)
            trend_response = collect_trends.run(
                canonical_name=group.canonical_name,
                queries=group.queries,
                datalab_service=self.datalab_service,
            )
            trend_repo.create_snapshot(
                query_group_id=query_entity.id,
                source="naver_datalab",
                window_start=datetime.combine(trend_response.startDate, datetime.min.time(), tzinfo=timezone.utc),
                window_end=datetime.combine(trend_response.endDate, datetime.min.time(), tzinfo=timezone.utc),
                target_key="baseline_12w_initial",
                request_payload_json=initial_request.model_dump(mode="json", exclude_none=True),
                raw_response_json=trend_response.model_dump(mode="json"),
            )

            features = compute_features.run(
                response=trend_response,
                query_count=len(group.queries),
                queries=group.queries,
                feature_service=self.feature_service,
            )
            combined_gtm_context = combine_online_gtm_contexts(
                naver_context=online_gtm_context,
                google_context=google_online_gtm_context,
                naver_weight=self.naver_search_service.settings.search_weight_naver_gtm,
                google_weight=self.naver_search_service.settings.search_weight_google_gtm,
            )
            if combined_gtm_context is not None:
                evidence_online_gtm = combine_search_channel_scores(
                    naver_score=(
                        self.naver_search_service.channel_classifier.score_from_context(online_gtm_context)
                        if online_gtm_context is not None
                        else None
                    ),
                    google_score=(
                        self.google_search_service.channel_classifier.score_from_context(google_online_gtm_context)
                        if google_online_gtm_context is not None
                        else None
                    ),
                    naver_weight=self.naver_search_service.settings.search_weight_naver_gtm,
                    google_weight=self.naver_search_service.settings.search_weight_google_gtm,
                )
                evidence_online_demand = combine_search_channel_scores(
                    naver_score=(
                        _context_demand_signal(online_gtm_context)
                        if online_gtm_context is not None
                        else None
                    ),
                    google_score=(
                        _context_demand_signal(google_online_gtm_context)
                        if google_online_gtm_context is not None
                        else None
                    ),
                    naver_weight=self.naver_search_service.settings.search_weight_naver_demand,
                    google_weight=self.naver_search_service.settings.search_weight_google_demand,
                )
                evidence_online_demand = min(1.0, max(features.online_demand_score, evidence_online_demand))
                evidence_whitespace = combine_search_channel_scores(
                    naver_score=(
                        online_gtm_context.competitive_whitespace_score
                        if online_gtm_context is not None
                        else None
                    ),
                    google_score=(
                        google_online_gtm_context.competitive_whitespace_score
                        if google_online_gtm_context is not None
                        else None
                    ),
                    naver_weight=self.naver_search_service.settings.search_weight_naver_gtm,
                    google_weight=self.naver_search_service.settings.search_weight_google_gtm,
                )
                evidence_keyword_difficulty = combine_search_channel_scores(
                    naver_score=(
                        self.naver_search_service.channel_classifier.keyword_difficulty_from_context(online_gtm_context)
                        if online_gtm_context is not None
                        else None
                    ),
                    google_score=(
                        self.google_search_service.channel_classifier.keyword_difficulty_from_context(google_online_gtm_context)
                        if google_online_gtm_context is not None
                        else None
                    ),
                    naver_weight=self.naver_search_service.settings.search_weight_naver_gtm,
                    google_weight=self.naver_search_service.settings.search_weight_google_gtm,
                )
                evidence_brand_dependency = combine_search_channel_scores(
                    naver_score=(
                        online_gtm_context.brand_concentration_score
                        if online_gtm_context is not None
                        else None
                    ),
                    google_score=(
                        google_online_gtm_context.brand_concentration_score
                        if google_online_gtm_context is not None
                        else None
                    ),
                    naver_weight=self.naver_search_service.settings.search_weight_naver_gtm,
                    google_weight=self.naver_search_service.settings.search_weight_google_gtm,
                )
                market_size_ceiling = estimate_market_size_ceiling_score(
                    market_size_context=market_size_context,
                    naver_total_results=search_evidence_context.total_results if search_evidence_context else None,
                    google_total_results=(
                        int(google_response.searchInformation.totalResults)
                        if "google_response" in locals() and google_online_gtm_context is not None
                        else None
                    ),
                )
                features = features.model_copy(
                    update={
                        "online_gtm_efficiency_score": round(evidence_online_gtm, 4),
                        "online_demand_score": round(evidence_online_demand, 4),
                        "competitive_whitespace_score": round(max(features.competitive_whitespace_score, evidence_whitespace), 4),
                        "brand_dependency_score": round(max(features.brand_dependency_score, evidence_brand_dependency), 4),
                        "keyword_difficulty_score": round(max(features.keyword_difficulty_score, evidence_keyword_difficulty), 4),
                        "market_size_ceiling_score": round(market_size_ceiling, 4),
                    }
                )
                online_gtm_context = combined_gtm_context
            else:
                features = features.model_copy(
                    update={
                        "market_size_ceiling_score": round(
                            estimate_market_size_ceiling_score(
                                market_size_context=market_size_context,
                                naver_total_results=search_evidence_context.total_results if search_evidence_context else None,
                                google_total_results=(
                                    int(google_response.searchInformation.totalResults)
                                    if "google_response" in locals()
                                    else None
                                ),
                            ),
                            4,
                        )
                    }
                )
            trend_repo.upsert_feature(query_group_id=query_entity.id, **features.model_dump())
            breakdown = score_candidates.run(
                candidate=candidate,
                features=features,
                scoring_service=self.scoring_service,
            )
            score_repo.create_score(
                problem_candidate_id=candidate_entity.id,
                trend_signal_score=breakdown.online_demand * 100,
                saas_fit_score=(
                    breakdown.repeated_pain + breakdown.problem_intensity + breakdown.implementation_feasibility
                )
                / 3
                * 100,
                implementation_score=breakdown.implementation_feasibility * 100,
                payment_score=breakdown.payment_likelihood * 100,
                final_score=breakdown.final_score,
                reasoning_summary=breakdown.reasoning_summary,
            )
            candidate_entity.status = CandidateStatus.SCORED.value

            scored_payloads.append(
                (
                    breakdown.final_score,
                    candidate_entity.id,
                    FinalAnalysisInput(
                        canonical_name=group.canonical_name,
                        persona=candidate.persona,
                        problem_summary=candidate.pain,
                        query_group=group.queries,
                        features=features,
                        score_breakdown=breakdown,
                        risk_flags=candidate.risk_flags,
                        market_size_context=market_size_context,
                        search_evidence_context=search_evidence_context,
                        shopping_evidence_context=shopping_evidence_context,
                        public_data_context=public_data_context,
                        online_gtm_context=online_gtm_context,
                    ),
                )
            )

        scored_payloads.sort(key=lambda item: item[0], reverse=True)
        reports = []
        for priority, (_, candidate_id, analysis_input) in enumerate(scored_payloads[:top_k], start=1):
            report = build_reports.run(payload=analysis_input, report_service=self.report_service)
            score_repo.create_report(
                problem_candidate_id=candidate_id,
                report_json=report.model_dump(mode="json"),
                recommended_priority=priority,
            )
            reports.append(report.model_copy(update={"recommended_priority": priority}))

        return PipelineRunResponse(
            seed_category_id=seed.id,
            generated_candidates=len(generated.candidates),
            scored_candidates=len(scored_payloads),
            reported_candidates=len(reports),
            reports=reports,
        )


def combine_search_channel_scores(
    *,
    naver_score: float | None,
    google_score: float | None,
    naver_weight: float,
    google_weight: float,
) -> float:
    available: list[tuple[float, float]] = []
    if naver_score is not None:
        available.append((naver_score, naver_weight))
    if google_score is not None:
        available.append((google_score, google_weight))
    if not available:
        return 0.0
    total_weight = sum(weight for _, weight in available)
    if total_weight <= 0:
        return sum(score for score, _ in available) / len(available)
    return sum(score * weight for score, weight in available) / total_weight


def combine_online_gtm_contexts(
    *,
    naver_context: OnlineGTMContext | None,
    google_context: OnlineGTMContext | None,
    naver_weight: float,
    google_weight: float,
) -> OnlineGTMContext | None:
    if naver_context is None and google_context is None:
        return None
    if naver_context is None:
        return google_context
    if google_context is None:
        return naver_context

    weights = [
        ("naver", naver_context, naver_weight),
        ("google", google_context, google_weight),
    ]
    score_fields = (
        "community_presence_score",
        "seo_discoverability_score",
        "competitor_presence_score",
        "brand_concentration_score",
        "competitive_whitespace_score",
    )
    merged_counts = {
        key: naver_context.channel_counts.get(key, 0) + google_context.channel_counts.get(key, 0)
        for key in set(naver_context.channel_counts) | set(google_context.channel_counts)
    }
    merged_domains = list(dict.fromkeys([*naver_context.competitor_domains, *google_context.competitor_domains]))

    merged_scores = {}
    for field in score_fields:
        weighted_value = combine_search_channel_scores(
            naver_score=getattr(naver_context, field),
            google_score=getattr(google_context, field),
            naver_weight=naver_weight,
            google_weight=google_weight,
        )
        merged_scores[field] = round(weighted_value, 4)

    merged_signals = list(dict.fromkeys([*naver_context.channel_signals, *google_context.channel_signals]))[:6]
    return OnlineGTMContext(
        query=naver_context.query,
        channel_signals=merged_signals,
        channel_counts=merged_counts,
        competitor_domains=merged_domains,
        community_presence_score=merged_scores["community_presence_score"],
        seo_discoverability_score=merged_scores["seo_discoverability_score"],
        competitor_presence_score=merged_scores["competitor_presence_score"],
        brand_concentration_score=merged_scores["brand_concentration_score"],
        competitive_whitespace_score=merged_scores["competitive_whitespace_score"],
        summary=(
            "검색 채널 근거를 Naver와 Google에서 합산했다. "
            f"Naver 비중 {naver_weight:.2f}, Google 비중 {google_weight:.2f}를 사용했다."
        ),
    )


def _context_demand_signal(context: OnlineGTMContext) -> float:
    return min(
        1.0,
        (
            (context.competitor_presence_score or 0.0) * 0.45
            + (context.seo_discoverability_score or 0.0) * 0.35
            + (context.community_presence_score or 0.0) * 0.2
        ),
    )


def estimate_market_size_ceiling_score(
    *,
    market_size_context: MarketSizeContext | None,
    naver_total_results: int | None,
    google_total_results: int | None,
) -> float:
    observed_business_scale = None
    if market_size_context is not None:
        observed_business_scale = market_size_context.business_count or market_size_context.employee_count

    business_score = None
    if observed_business_scale is not None:
        if observed_business_scale <= 3_000:
            business_score = 0.96
        elif observed_business_scale <= 20_000:
            business_score = 0.86
        elif observed_business_scale <= 80_000:
            business_score = 0.68
        elif observed_business_scale <= 200_000:
            business_score = 0.4
        else:
            business_score = 0.2

    totals = [value for value in (naver_total_results, google_total_results) if value is not None]
    serp_score = None
    if totals:
        average_total = sum(totals) / len(totals)
        if average_total <= 1_000:
            serp_score = 0.9
        elif average_total <= 10_000:
            serp_score = 0.72
        elif average_total <= 100_000:
            serp_score = 0.42
        else:
            serp_score = 0.18

    available = [value for value in (business_score, serp_score) if value is not None]
    if not available:
        return 0.7
    if len(available) == 1:
        return available[0]
    return round((business_score * 0.65) + (serp_score * 0.35), 4)
