"""Fix collection schedule uniqueness to allow multiple sources per query group."""

from alembic import op


revision = "20260406_0003"
down_revision = "20260406_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("collection_schedules") as batch_op:
        batch_op.drop_constraint("uq_collection_schedules_query_group", type_="unique")
        batch_op.create_unique_constraint(
            "uq_collection_schedules_query_group_source",
            ["query_group_id", "source"],
        )


def downgrade() -> None:
    with op.batch_alter_table("collection_schedules") as batch_op:
        batch_op.drop_constraint("uq_collection_schedules_query_group_source", type_="unique")
        batch_op.create_unique_constraint("uq_collection_schedules_query_group", ["query_group_id"])
