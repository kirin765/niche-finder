from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from micro_niche_finder.config.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SeedCategory(Base):
    __tablename__ = "seed_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    problem_candidates: Mapped[list[ProblemCandidate]] = relationship(back_populates="seed_category")


class ProblemCandidate(Base):
    __tablename__ = "problem_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seed_category_id: Mapped[int] = mapped_column(ForeignKey("seed_categories.id"), nullable=False)
    persona: Mapped[str] = mapped_column(String(255), nullable=False)
    job_to_be_done: Mapped[str] = mapped_column(Text, nullable=False)
    pain: Mapped[str] = mapped_column(Text, nullable=False)
    repeat_frequency: Mapped[str] = mapped_column(String(32), nullable=False)
    current_workaround_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    software_fit: Mapped[str] = mapped_column(String(32), nullable=False)
    payment_likelihood: Mapped[str] = mapped_column(String(32), nullable=False)
    risk_flags_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="generated")
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False, default="candidate_generation.v1")
    schema_version: Mapped[str] = mapped_column(String(16), nullable=False, default="1.0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    seed_category: Mapped[SeedCategory] = relationship(back_populates="problem_candidates")
    query_groups: Mapped[list[QueryGroup]] = relationship(back_populates="problem_candidate")
    niche_scores: Mapped[list[NicheScore]] = relationship(back_populates="problem_candidate")
    final_reports: Mapped[list[FinalReport]] = relationship(back_populates="problem_candidate")


class QueryGroup(Base):
    __tablename__ = "query_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    problem_candidate_id: Mapped[int] = mapped_column(ForeignKey("problem_candidates.id"), nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    queries_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    excluded_queries_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    overlap_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    problem_candidate: Mapped[ProblemCandidate] = relationship(back_populates="query_groups")
    trend_snapshots: Mapped[list[TrendSnapshot]] = relationship(back_populates="query_group")
    features: Mapped[list[Feature]] = relationship(back_populates="query_group")


class TrendSnapshot(Base):
    __tablename__ = "trend_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    query_group_id: Mapped[int] = mapped_column(ForeignKey("query_groups.id"), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_response_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    query_group: Mapped[QueryGroup] = relationship(back_populates="trend_snapshots")


class Feature(Base):
    __tablename__ = "features"
    __table_args__ = (UniqueConstraint("query_group_id", name="uq_features_query_group"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    query_group_id: Mapped[int] = mapped_column(ForeignKey("query_groups.id"), nullable=False)
    recent_growth_4w: Mapped[float] = mapped_column(Float, nullable=False)
    recent_growth_12w: Mapped[float] = mapped_column(Float, nullable=False)
    moving_avg_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    volatility: Mapped[float] = mapped_column(Float, nullable=False)
    spike_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    decay_after_peak: Mapped[float] = mapped_column(Float, nullable=False)
    seasonality_score: Mapped[float] = mapped_column(Float, nullable=False)
    age_concentration: Mapped[float] = mapped_column(Float, nullable=False)
    gender_concentration: Mapped[float] = mapped_column(Float, nullable=False)
    mobile_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    segment_consistency: Mapped[float] = mapped_column(Float, nullable=False)
    query_diversity: Mapped[float] = mapped_column(Float, nullable=False)
    problem_specificity: Mapped[float] = mapped_column(Float, nullable=False)
    commercial_intent_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    brand_dependency_score: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    query_group: Mapped[QueryGroup] = relationship(back_populates="features")


class NicheScore(Base):
    __tablename__ = "niche_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    problem_candidate_id: Mapped[int] = mapped_column(ForeignKey("problem_candidates.id"), nullable=False)
    trend_signal_score: Mapped[float] = mapped_column(Float, nullable=False)
    saas_fit_score: Mapped[float] = mapped_column(Float, nullable=False)
    implementation_score: Mapped[float] = mapped_column(Float, nullable=False)
    payment_score: Mapped[float] = mapped_column(Float, nullable=False)
    final_score: Mapped[float] = mapped_column(Float, nullable=False)
    reasoning_summary: Mapped[str] = mapped_column(Text, nullable=False)
    weights_version: Mapped[str] = mapped_column(String(32), nullable=False, default="default.v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    problem_candidate: Mapped[ProblemCandidate] = relationship(back_populates="niche_scores")


class FinalReport(Base):
    __tablename__ = "final_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    problem_candidate_id: Mapped[int] = mapped_column(ForeignKey("problem_candidates.id"), nullable=False)
    report_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    recommended_priority: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    problem_candidate: Mapped[ProblemCandidate] = relationship(back_populates="final_reports")
