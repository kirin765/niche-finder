"""Add micro ceiling and whitespace feature fields, remove unused demographic fields."""

from alembic import op
import sqlalchemy as sa


revision = "20260407_0005"
down_revision = "20260406_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_columns = {column["name"] for column in sa.inspect(bind).get_columns("features")}

    if "market_size_ceiling_score" not in existing_columns:
        op.add_column(
            "features",
            sa.Column("market_size_ceiling_score", sa.Float(), nullable=False, server_default="0.7"),
        )
    if "competitive_whitespace_score" not in existing_columns:
        op.add_column(
            "features",
            sa.Column("competitive_whitespace_score", sa.Float(), nullable=False, server_default="0.6"),
        )

    for column_name in ("age_concentration", "gender_concentration", "mobile_ratio", "segment_consistency"):
        if column_name in existing_columns:
            op.drop_column("features", column_name)


def downgrade() -> None:
    bind = op.get_bind()
    existing_columns = {column["name"] for column in sa.inspect(bind).get_columns("features")}

    for column_name in ("age_concentration", "gender_concentration", "mobile_ratio", "segment_consistency"):
        if column_name not in existing_columns:
            op.add_column("features", sa.Column(column_name, sa.Float(), nullable=False, server_default="0.0"))

    if "competitive_whitespace_score" in existing_columns:
        op.drop_column("features", "competitive_whitespace_score")
    if "market_size_ceiling_score" in existing_columns:
        op.drop_column("features", "market_size_ceiling_score")
