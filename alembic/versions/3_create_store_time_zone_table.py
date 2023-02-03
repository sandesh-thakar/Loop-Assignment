"""create store time zone table

Revision ID: 3
Revises: 2
Create Date: 2023-01-28 13:18:36.048325

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "3"
down_revision = "2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "store_time_zone",
        sa.Column("store_id", sa.String(), primary_key=True),
        sa.Column("timezone_str", sa.String()),
    )


def downgrade() -> None:
    op.drop_table("store_time_zone")
