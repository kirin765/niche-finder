"""Add online demand scoring fields to features."""

from alembic import op
import sqlalchemy as sa


revision = "20260406_0004"
down_revision = "20260406_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_columns = {column["name"] for column in sa.inspect(bind).get_columns("features")}

    if "online_demand_score" not in existing_columns:
        op.add_column(
            "features",
            sa.Column("online_demand_score", sa.Float(), nullable=False, server_default="0.5"),
        )
    if "market_size_sufficiency_score" not in existing_columns:
        op.add_column(
            "features",
            sa.Column("market_size_sufficiency_score", sa.Float(), nullable=False, server_default="0.5"),
        )
    if "online_gtm_efficiency_score" not in existing_columns:
        op.add_column(
            "features",
            sa.Column("online_gtm_efficiency_score", sa.Float(), nullable=False, server_default="0.5"),
        )


def downgrade() -> None:
    op.drop_column("features", "online_gtm_efficiency_score")
    op.drop_column("features", "market_size_sufficiency_score")
    op.drop_column("features", "online_demand_score")
