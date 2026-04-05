from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from micro_niche_finder.domain.models import Feature, TrendSnapshot


class TrendRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_snapshot(self, **kwargs) -> TrendSnapshot:
        entity = TrendSnapshot(**kwargs)
        self.session.add(entity)
        self.session.flush()
        return entity

    def upsert_feature(self, query_group_id: int, **kwargs) -> Feature:
        existing = self.session.scalar(select(Feature).where(Feature.query_group_id == query_group_id))
        if existing:
            for key, value in kwargs.items():
                setattr(existing, key, value)
            return existing
        entity = Feature(query_group_id=query_group_id, **kwargs)
        self.session.add(entity)
        self.session.flush()
        return entity

    def delete_snapshots_for_group(self, query_group_id: int) -> None:
        self.session.execute(delete(TrendSnapshot).where(TrendSnapshot.query_group_id == query_group_id))
