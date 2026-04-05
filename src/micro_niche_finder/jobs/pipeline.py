from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from micro_niche_finder.domain.enums import CandidateStatus
from micro_niche_finder.domain.schemas import FinalAnalysisInput, PipelineRunResponse
from micro_niche_finder.jobs import build_reports, collect_trends, compute_features, generate_candidates, score_candidates
from micro_niche_finder.repos.candidate_repo import CandidateRepository, QueryGroupRepository, SeedCategoryRepository
from micro_niche_finder.repos.score_repo import ScoreRepository
from micro_niche_finder.repos.trend_repo import TrendRepository
from micro_niche_finder.services.clustering_service import QueryClusteringService
from micro_niche_finder.services.datalab_service import NaverDataLabService
from micro_niche_finder.services.feature_service import FeatureExtractionService
from micro_niche_finder.services.llm_service import OpenAIResearchService
from micro_niche_finder.services.report_service import ReportService
from micro_niche_finder.services.scoring_service import ScoringService


class PipelineService:
    def __init__(
        self,
        *,
        llm_service: OpenAIResearchService,
        datalab_service: NaverDataLabService,
        clustering_service: QueryClusteringService,
        feature_service: FeatureExtractionService,
        scoring_service: ScoringService,
        report_service: ReportService,
    ) -> None:
        self.llm_service = llm_service
        self.datalab_service = datalab_service
        self.clustering_service = clustering_service
        self.feature_service = feature_service
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
        trend_repo = TrendRepository(session)
        score_repo = ScoreRepository(session)

        seed = seed_repo.get(seed_category_id)
        if seed is None:
            raise ValueError(f"Seed category {seed_category_id} not found")

        generated = generate_candidates.run(seed.name, candidate_count, self.llm_service)
        expansions = [self.llm_service.expand_queries(candidate) for candidate in generated.candidates]
        clustered = self.clustering_service.cluster_candidates(expansions)

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
