"""Add payability and absolute demand fields to features."""

from alembic import op
import sqlalchemy as sa


revision = "20260407_0007"
down_revision = "20260407_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_columns = {column["name"] for column in sa.inspect(bind).get_columns("features")}

    if "absolute_demand_score" not in existing_columns:
        op.add_column("features", sa.Column("absolute_demand_score", sa.Float(), nullable=False, server_default="0.5"))
    if "payability_score" not in existing_columns:
        op.add_column("features", sa.Column("payability_score", sa.Float(), nullable=False, server_default="0.5"))


def downgrade() -> None:
    bind = op.get_bind()
    existing_columns = {column["name"] for column in sa.inspect(bind).get_columns("features")}
    if "payability_score" in existing_columns:
        op.drop_column("features", "payability_score")
    if "absolute_demand_score" in existing_columns:
        op.drop_column("features", "absolute_demand_score")
