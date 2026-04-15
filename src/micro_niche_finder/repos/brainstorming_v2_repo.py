from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from micro_niche_finder.domain.models import (
    ClusterMember,
    EvidencePacket,
    IdeaCandidateV2,
    IdeaScoreV2,
    ProblemCluster,
    ProblemSignal,
    SignalEvent,
)


class SignalEventRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, **kwargs) -> SignalEvent:
        entity = SignalEvent(**kwargs)
        self.session.add(entity)
        self.session.flush()
        return entity


class ProblemSignalRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, **kwargs) -> ProblemSignal:
        entity = ProblemSignal(**kwargs)
        self.session.add(entity)
        self.session.flush()
        return entity

    def list_recent(self, limit: int = 200) -> list[ProblemSignal]:
        stmt = select(ProblemSignal).order_by(ProblemSignal.created_at.desc()).limit(limit)
        return list(self.session.scalars(stmt))


class ProblemClusterRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, **kwargs) -> ProblemCluster:
        entity = ProblemCluster(**kwargs)
        self.session.add(entity)
        self.session.flush()
        return entity

    def list_recent(self, limit: int = 100) -> list[ProblemCluster]:
        stmt = select(ProblemCluster).order_by(ProblemCluster.updated_at.desc()).limit(limit)
        return list(self.session.scalars(stmt))


class ClusterMemberRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, **kwargs) -> ClusterMember:
        entity = ClusterMember(**kwargs)
        self.session.add(entity)
        self.session.flush()
        return entity


class IdeaCandidateV2Repository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, **kwargs) -> IdeaCandidateV2:
        entity = IdeaCandidateV2(**kwargs)
        self.session.add(entity)
        self.session.flush()
        return entity


class EvidencePacketRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, **kwargs) -> EvidencePacket:
        entity = EvidencePacket(**kwargs)
        self.session.add(entity)
        self.session.flush()
        return entity


class IdeaScoreV2Repository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, **kwargs) -> IdeaScoreV2:
        entity = IdeaScoreV2(**kwargs)
        self.session.add(entity)
        self.session.flush()
        return entity
