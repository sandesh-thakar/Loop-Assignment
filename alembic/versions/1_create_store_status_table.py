"""create store status table

Revision ID: 1
Revises:
Create Date: 2023-01-27 20:43:44.008920

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "1"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "store_status",
        sa.Column("store_status_id", sa.BIGINT, primary_key=True, autoincrement=True),
        sa.Column("store_id", sa.String(), index=True),
        sa.Column("timestamp_utc", sa.DateTime()),
        sa.Column("status", sa.String()),
    )


def downgrade() -> None:
    op.drop_table("store_status")
