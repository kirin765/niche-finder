from sqlalchemy import select
from sqlalchemy.orm import Session

from micro_niche_finder.domain.models import FinalReport, NicheScore


class ScoreRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_score(self, **kwargs) -> NicheScore:
        entity = NicheScore(**kwargs)
        self.session.add(entity)
        self.session.flush()
        return entity

    def create_report(self, **kwargs) -> FinalReport:
        entity = FinalReport(**kwargs)
        self.session.add(entity)
        self.session.flush()
        return entity

    def list_scores(self, limit: int) -> list[NicheScore]:
        stmt = select(NicheScore).order_by(NicheScore.final_score.desc()).limit(limit)
        return list(self.session.scalars(stmt))
