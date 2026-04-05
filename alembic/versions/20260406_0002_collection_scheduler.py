"""Add collection scheduling and API budget tables."""

from alembic import op
import sqlalchemy as sa


revision = "20260406_0002"
down_revision = "20260405_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("trend_snapshots", sa.Column("target_key", sa.String(length=64), nullable=True))
    op.add_column("trend_snapshots", sa.Column("request_payload_json", sa.JSON(), nullable=True))

    op.create_table(
        "collection_schedules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("query_group_id", sa.Integer(), sa.ForeignKey("query_groups.id"), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("cadence_minutes", sa.Integer(), nullable=False),
        sa.Column("collection_targets_json", sa.JSON(), nullable=False),
        sa.Column("next_target_index", sa.Integer(), nullable=False),
        sa.Column("last_collected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_collect_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_status", sa.String(length=32), nullable=True),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("query_group_id", name="uq_collection_schedules_query_group"),
    )
    op.create_table(
        "api_usage_counters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("daily_limit", sa.Integer(), nullable=False),
        sa.Column("calls_made", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source", "usage_date", name="uq_api_usage_source_date"),
    )


def downgrade() -> None:
    op.drop_table("api_usage_counters")
    op.drop_table("collection_schedules")
    op.drop_column("trend_snapshots", "request_payload_json")
    op.drop_column("trend_snapshots", "target_key")
