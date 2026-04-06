from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from micro_niche_finder.config.database import Base
from micro_niche_finder.domain.models import (
    CollectionSchedule,
    Feature,
    FinalReport,
    NicheScore,
    ProblemCandidate,
    QueryGroup,
    SeedCategory,
    TrendSnapshot,
)
from micro_niche_finder.services.vertical_seed_migration_service import (
    CURATED_VERTICAL_SEEDS,
    VerticalSeedMigrationService,
)


def _build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)()


def test_vertical_seed_migration_removes_horizontal_seed_graph_and_inserts_curated_verticals() -> None:
    session = _build_session()
    horizontal_seed = SeedCategory(name="예약·일정관리", description="업종 구분 없이 예약과 일정 관리")
    vertical_seed = SeedCategory(name="학원 운영", description="출결과 보강 관리")
    session.add_all([horizontal_seed, vertical_seed])
    session.flush()

    candidate = ProblemCandidate(
        seed_category_id=horizontal_seed.id,
        persona="원장",
        job_to_be_done="예약을 정리한다",
        pain="누락이 생긴다",
        repeat_frequency="daily",
        current_workaround_json=["엑셀"],
        software_fit="high",
        payment_likelihood="medium",
        risk_flags_json=[],
        status="generated",
        prompt_version="candidate_generation.v1",
        schema_version="1.0",
    )
    session.add(candidate)
    session.flush()

    query_group = QueryGroup(
        problem_candidate_id=candidate.id,
        canonical_name="학원 보강 관리",
        queries_json=["학원 보강 관리"],
        excluded_queries_json=[],
        overlap_score=0.8,
    )
    session.add(query_group)
    session.flush()

    session.add_all(
        [
            TrendSnapshot(
                query_group_id=query_group.id,
                source="naver_datalab",
                window_start=horizontal_seed.created_at,
                window_end=horizontal_seed.created_at,
                target_key="baseline",
                request_payload_json={},
                raw_response_json={},
            ),
            Feature(
                query_group_id=query_group.id,
                recent_growth_4w=0.1,
                recent_growth_12w=0.1,
                moving_avg_ratio=1.0,
                volatility=0.2,
                spike_ratio=0.1,
                decay_after_peak=0.0,
                seasonality_score=0.1,
                query_diversity=0.5,
                problem_specificity=0.6,
                commercial_intent_ratio=0.7,
                brand_dependency_score=0.1,
                online_demand_score=0.5,
                absolute_demand_score=0.5,
                payability_score=0.5,
                market_size_sufficiency_score=0.5,
                online_gtm_efficiency_score=0.5,
                market_size_ceiling_score=0.8,
                competitive_whitespace_score=0.6,
                keyword_difficulty_score=0.4,
            ),
            CollectionSchedule(
                query_group_id=query_group.id,
                source="naver_datalab",
                collection_targets_json=[],
                next_collect_at=horizontal_seed.created_at,
            ),
            NicheScore(
                problem_candidate_id=candidate.id,
                trend_signal_score=50.0,
                saas_fit_score=70.0,
                implementation_score=80.0,
                payment_score=60.0,
                final_score=72.0,
                reasoning_summary="summary",
                weights_version="default.v1",
            ),
            FinalReport(
                problem_candidate_id=candidate.id,
                report_json={"niche_name": "학원 보강 관리"},
                recommended_priority=1,
            ),
        ]
    )
    session.commit()

    service = VerticalSeedMigrationService()
    summary = service.migrate(session)
    session.commit()

    names = list(session.scalars(select(SeedCategory.name).order_by(SeedCategory.name.asc())))
    assert "예약·일정관리" not in names
    assert "학원 운영" in names
    assert set(name for name, _ in CURATED_VERTICAL_SEEDS).issubset(set(names))
    assert summary.removed_seed_names == ["예약·일정관리"]
    assert summary.deleted_candidate_count == 1
    assert summary.deleted_query_group_count == 1
    assert session.scalar(select(ProblemCandidate.id)) is None
    assert session.scalar(select(QueryGroup.id)) is None
    assert session.scalar(select(TrendSnapshot.id)) is None
    assert session.scalar(select(Feature.id)) is None
    assert session.scalar(select(CollectionSchedule.id)) is None
    assert session.scalar(select(NicheScore.id)) is None
    assert session.scalar(select(FinalReport.id)) is None


def test_vertical_seed_migration_dry_run_is_non_destructive() -> None:
    session = _build_session()
    session.add(SeedCategory(name="고객응대·문의관리", description="업종 구분 없는 문의 관리"))
    session.commit()

    service = VerticalSeedMigrationService()
    summary = service.migrate(session, dry_run=True)

    names = list(session.scalars(select(SeedCategory.name)))
    assert names == ["고객응대·문의관리"]
    assert summary.removed_seed_names == ["고객응대·문의관리"]
    assert "스마트스토어 운영" in summary.inserted_seed_names
