from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from micro_niche_finder.domain.enums import CandidateStatus
from micro_niche_finder.domain.schemas import (
    FinalAnalysisInput,
    MarketSizeContext,
    NaverSearchRequest,
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
                source="google_custom_search",
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
                collection_repo.upsert_schedule(
                    query_group_id=query_entity.id,
                    source=KosisEmployeeService.SOURCE,
                    priority=max(1, self.collection_scheduler_service.settings.collector_default_priority - 10),
                    cadence_minutes=self.collection_scheduler_service.settings.kosis_employee_cadence_minutes,
                    collection_targets_json=[
                        target.model_dump(mode="json")
                        for target in self.collection_scheduler_service.kosis_default_targets(selection)
                    ],
                    next_collect_at=self.collection_scheduler_service.default_next_collect_at(),
                )
                try:
                    kosis_request = self.kosis_employee_service.build_request(selection)
                    kosis_response = self.kosis_employee_service.fetch(kosis_request)
                    trend_repo.create_snapshot(
                        query_group_id=query_entity.id,
                        source=KosisEmployeeService.SOURCE,
                        window_start=datetime(kosis_response.reference_year, 1, 1, tzinfo=timezone.utc),
                        window_end=datetime(kosis_response.reference_year, 12, 31, tzinfo=timezone.utc),
                        target_key="kosis_employee_count_initial",
                        request_payload_json=kosis_request.model_dump(mode="json"),
                        raw_response_json=kosis_response.model_dump(mode="json"),
                    )
                    market_size_context = self.kosis_employee_service.build_market_size_context(
                        kosis_response,
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
                        summary=f"KOSIS 종사자 수 조회에 실패했다: {exc}",
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
            except Exception:
                search_evidence_context = None

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
                feature_service=self.feature_service,
            )
            trend_repo.upsert_feature(query_group_id=query_entity.id, **features.model_dump())
            breakdown = score_candidates.run(
                candidate=candidate,
                features=features,
                scoring_service=self.scoring_service,
            )
            score_repo.create_score(
                problem_candidate_id=candidate_entity.id,
                trend_signal_score=breakdown.persistent_signal * 100,
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
