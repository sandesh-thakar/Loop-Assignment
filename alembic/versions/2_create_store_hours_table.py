"""create store hours table

Revision ID: 2
Revises: 1
Create Date: 2023-01-28 12:46:47.308903

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "2"
down_revision = "1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "store_hours",
        sa.Column("store_hours_id", sa.BIGINT, primary_key=True, autoincrement=True),
        sa.Column("store_id", sa.String(), index=True),
        sa.Column("day", sa.Integer()),
        sa.Column("start_time_local", sa.Time()),
        sa.Column("end_time_local", sa.Time()),
        sa.Index("store_hours_idx", "store_id", "day"),
    )


def downgrade() -> None:
    op.drop_table("store_hours")
