from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from micro_niche_finder.domain.models import FinalReport, ProblemCandidate, QueryGroup, SeedCategory
from micro_niche_finder.domain.schemas import FinalReportRead


class SeedCategoryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, name: str, description: str | None) -> SeedCategory:
        entity = SeedCategory(name=name, description=description)
        self.session.add(entity)
        self.session.flush()
        return entity

    def get(self, seed_category_id: int) -> SeedCategory | None:
        stmt = select(SeedCategory).where(SeedCategory.id == seed_category_id)
        return self.session.scalar(stmt)

    def list_all(self) -> list[SeedCategory]:
        stmt = select(SeedCategory).order_by(SeedCategory.created_at.desc())
        return list(self.session.scalars(stmt))

    def list_reports(self, limit: int) -> list[FinalReportRead]:
        stmt = select(FinalReport).order_by(FinalReport.recommended_priority.asc()).limit(limit)
        return [FinalReportRead.model_validate(item) for item in self.session.scalars(stmt)]


class CandidateRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, **kwargs) -> ProblemCandidate:
        entity = ProblemCandidate(**kwargs)
        self.session.add(entity)
        self.session.flush()
        return entity

    def list_for_seed(self, seed_category_id: int) -> list[ProblemCandidate]:
        stmt = (
            select(ProblemCandidate)
            .where(ProblemCandidate.seed_category_id == seed_category_id)
            .options(joinedload(ProblemCandidate.query_groups), joinedload(ProblemCandidate.niche_scores))
            .order_by(ProblemCandidate.created_at.asc())
        )
        return list(self.session.scalars(stmt).unique())


class QueryGroupRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, **kwargs) -> QueryGroup:
        entity = QueryGroup(**kwargs)
        self.session.add(entity)
        self.session.flush()
        return entity
