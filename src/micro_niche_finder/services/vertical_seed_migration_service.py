from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

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


CURATED_VERTICAL_SEEDS: tuple[tuple[str, str], ...] = (
    ("스마트스토어 운영", "소형 셀러의 상품관리, 가격확인, 리뷰대응, 정산 점검 같은 반복 업무를 다룬다."),
    ("학원 운영", "출결, 보강, 상담, 학부모 공지, 수납 확인 등 학원 운영 반복 업무를 다룬다."),
    ("병원 상담 운영", "예약 리마인드, 상담 후속조치, 문의 분류, 재내원 유도 업무를 다룬다."),
    ("부동산 중개 운영", "매물 추적, 고객 문의 응대, 방문 일정 조율, 계약 진행 관리를 다룬다."),
    ("미용실 운영", "예약, 재방문 관리, 시술 전후 상담, 노쇼 대응, 직원 스케줄 조정을 다룬다."),
    ("식당 운영", "재고 확인, 발주, 예약, 리뷰 대응, 배달 채널 운영 업무를 다룬다."),
    ("세무사 사무소 운영", "자료 요청, 마감 추적, 고객 커뮤니케이션, 신고 일정 관리 업무를 다룬다."),
    ("인테리어 견적 운영", "리드 접수, 상담 기록, 견적 비교, 일정 조율, 후속 응대 업무를 다룬다."),
)

KNOWN_HORIZONTAL_SEED_NAMES = {
    "예약·일정관리",
    "고객응대·문의관리",
    "정산·매출관리",
    "매출·정산관리",
}

HORIZONTAL_SOFTWARE_TOKENS = (
    "crm",
    "erp",
    "groupware",
    "project management",
    "marketing automation",
    "hr",
    "accounting",
    "그룹웨어",
    "프로젝트 관리",
    "마케팅 자동화",
    "인사관리",
    "회계관리",
)

GENERIC_WORKFLOW_TOKENS = (
    "예약",
    "일정",
    "문의",
    "고객응대",
    "상담",
    "정산",
    "매출",
)

VERTICAL_HINT_TOKENS = (
    "스마트스토어",
    "셀러",
    "학원",
    "병원",
    "클리닉",
    "의원",
    "부동산",
    "중개",
    "미용실",
    "식당",
    "카페",
    "세무사",
    "회계사무소",
    "인테리어",
    "견적",
)


@dataclass(slots=True)
class VerticalSeedMigrationSummary:
    removed_seed_names: list[str]
    inserted_seed_names: list[str]
    kept_seed_names: list[str]
    deleted_candidate_count: int
    deleted_query_group_count: int


class VerticalSeedMigrationService:
    def __init__(self, curated_seeds: tuple[tuple[str, str], ...] = CURATED_VERTICAL_SEEDS) -> None:
        self.curated_seeds = curated_seeds

    def migrate(self, session: Session, *, dry_run: bool = False) -> VerticalSeedMigrationSummary:
        seeds = list(session.scalars(select(SeedCategory).order_by(SeedCategory.id.asc())))
        seeds_to_remove = [seed for seed in seeds if self._is_horizontal_seed(seed.name, seed.description)]
        removed_seed_names = [seed.name for seed in seeds_to_remove]
        kept_seed_names = [seed.name for seed in seeds if seed.name not in removed_seed_names]

        candidate_ids: list[int] = []
        query_group_ids: list[int] = []
        if seeds_to_remove:
            seed_ids = [seed.id for seed in seeds_to_remove]
            candidate_ids = list(
                session.scalars(
                    select(ProblemCandidate.id).where(ProblemCandidate.seed_category_id.in_(seed_ids))
                )
            )
            if candidate_ids:
                query_group_ids = list(
                    session.scalars(
                        select(QueryGroup.id).where(QueryGroup.problem_candidate_id.in_(candidate_ids))
                    )
                )

        existing_names_after_cleanup = set(kept_seed_names)
        inserted_seed_names = [name for name, _ in self.curated_seeds if name not in existing_names_after_cleanup]

        if dry_run:
            return VerticalSeedMigrationSummary(
                removed_seed_names=removed_seed_names,
                inserted_seed_names=inserted_seed_names,
                kept_seed_names=kept_seed_names,
                deleted_candidate_count=len(candidate_ids),
                deleted_query_group_count=len(query_group_ids),
            )

        if query_group_ids:
            session.execute(delete(TrendSnapshot).where(TrendSnapshot.query_group_id.in_(query_group_ids)))
            session.execute(delete(Feature).where(Feature.query_group_id.in_(query_group_ids)))
            session.execute(delete(CollectionSchedule).where(CollectionSchedule.query_group_id.in_(query_group_ids)))
        if candidate_ids:
            session.execute(delete(FinalReport).where(FinalReport.problem_candidate_id.in_(candidate_ids)))
            session.execute(delete(NicheScore).where(NicheScore.problem_candidate_id.in_(candidate_ids)))
            session.execute(delete(QueryGroup).where(QueryGroup.problem_candidate_id.in_(candidate_ids)))
            session.execute(delete(ProblemCandidate).where(ProblemCandidate.id.in_(candidate_ids)))
        if seeds_to_remove:
            session.execute(delete(SeedCategory).where(SeedCategory.id.in_([seed.id for seed in seeds_to_remove])))

        for name, description in self.curated_seeds:
            if session.scalar(select(SeedCategory).where(SeedCategory.name == name)) is None:
                session.add(SeedCategory(name=name, description=description))

        session.flush()
        final_names = list(session.scalars(select(SeedCategory.name).order_by(SeedCategory.id.asc())))
        return VerticalSeedMigrationSummary(
            removed_seed_names=removed_seed_names,
            inserted_seed_names=inserted_seed_names,
            kept_seed_names=[name for name in final_names if name not in inserted_seed_names],
            deleted_candidate_count=len(candidate_ids),
            deleted_query_group_count=len(query_group_ids),
        )

    def _is_horizontal_seed(self, name: str, description: str | None) -> bool:
        normalized_name = name.replace(" ", "")
        if normalized_name in KNOWN_HORIZONTAL_SEED_NAMES:
            return True

        haystack = f"{name} {description or ''}".lower()
        if any(token in haystack for token in HORIZONTAL_SOFTWARE_TOKENS):
            return True

        if any(token in name for token in GENERIC_WORKFLOW_TOKENS) and not any(
            hint in haystack for hint in VERTICAL_HINT_TOKENS
        ):
            return True

        return False
