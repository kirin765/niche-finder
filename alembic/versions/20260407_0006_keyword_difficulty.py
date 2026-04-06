"""Add keyword difficulty score to features."""

from alembic import op
import sqlalchemy as sa


revision = "20260407_0006"
down_revision = "20260407_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_columns = {column["name"] for column in sa.inspect(bind).get_columns("features")}
    if "keyword_difficulty_score" not in existing_columns:
        op.add_column(
            "features",
            sa.Column("keyword_difficulty_score", sa.Float(), nullable=False, server_default="0.5"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    existing_columns = {column["name"] for column in sa.inspect(bind).get_columns("features")}
    if "keyword_difficulty_score" in existing_columns:
        op.drop_column("features", "keyword_difficulty_score")
