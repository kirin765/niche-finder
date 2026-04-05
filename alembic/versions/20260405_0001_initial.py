"""Initial schema."""

from alembic import op
import sqlalchemy as sa


revision = "20260405_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "seed_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "problem_candidates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("seed_category_id", sa.Integer(), sa.ForeignKey("seed_categories.id"), nullable=False),
        sa.Column("persona", sa.String(length=255), nullable=False),
        sa.Column("job_to_be_done", sa.Text(), nullable=False),
        sa.Column("pain", sa.Text(), nullable=False),
        sa.Column("repeat_frequency", sa.String(length=32), nullable=False),
        sa.Column("current_workaround_json", sa.JSON(), nullable=False),
        sa.Column("software_fit", sa.String(length=32), nullable=False),
        sa.Column("payment_likelihood", sa.String(length=32), nullable=False),
        sa.Column("risk_flags_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "query_groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("problem_candidate_id", sa.Integer(), sa.ForeignKey("problem_candidates.id"), nullable=False),
        sa.Column("canonical_name", sa.String(length=255), nullable=False),
        sa.Column("queries_json", sa.JSON(), nullable=False),
        sa.Column("excluded_queries_json", sa.JSON(), nullable=False),
        sa.Column("overlap_score", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "trend_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("query_group_id", sa.Integer(), sa.ForeignKey("query_groups.id"), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_response_json", sa.JSON(), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "features",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("query_group_id", sa.Integer(), sa.ForeignKey("query_groups.id"), nullable=False),
        sa.Column("recent_growth_4w", sa.Float(), nullable=False),
        sa.Column("recent_growth_12w", sa.Float(), nullable=False),
        sa.Column("moving_avg_ratio", sa.Float(), nullable=False),
        sa.Column("volatility", sa.Float(), nullable=False),
        sa.Column("spike_ratio", sa.Float(), nullable=False),
        sa.Column("decay_after_peak", sa.Float(), nullable=False),
        sa.Column("seasonality_score", sa.Float(), nullable=False),
        sa.Column("age_concentration", sa.Float(), nullable=False),
        sa.Column("gender_concentration", sa.Float(), nullable=False),
        sa.Column("mobile_ratio", sa.Float(), nullable=False),
        sa.Column("segment_consistency", sa.Float(), nullable=False),
        sa.Column("query_diversity", sa.Float(), nullable=False),
        sa.Column("problem_specificity", sa.Float(), nullable=False),
        sa.Column("commercial_intent_ratio", sa.Float(), nullable=False),
        sa.Column("brand_dependency_score", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("query_group_id", name="uq_features_query_group"),
    )
    op.create_table(
        "niche_scores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("problem_candidate_id", sa.Integer(), sa.ForeignKey("problem_candidates.id"), nullable=False),
        sa.Column("trend_signal_score", sa.Float(), nullable=False),
        sa.Column("saas_fit_score", sa.Float(), nullable=False),
        sa.Column("implementation_score", sa.Float(), nullable=False),
        sa.Column("payment_score", sa.Float(), nullable=False),
        sa.Column("final_score", sa.Float(), nullable=False),
        sa.Column("reasoning_summary", sa.Text(), nullable=False),
        sa.Column("weights_version", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "final_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("problem_candidate_id", sa.Integer(), sa.ForeignKey("problem_candidates.id"), nullable=False),
        sa.Column("report_json", sa.JSON(), nullable=False),
        sa.Column("recommended_priority", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("final_reports")
    op.drop_table("niche_scores")
    op.drop_table("features")
    op.drop_table("trend_snapshots")
    op.drop_table("query_groups")
    op.drop_table("problem_candidates")
    op.drop_table("seed_categories")
