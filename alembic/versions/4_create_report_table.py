"""create report table

Revision ID: 4
Revises: 3
Create Date: 2023-01-28 13:38:29.568219

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "4"
down_revision = "3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "report",
        sa.Column("report_id", sa.String(), primary_key=True),
        sa.Column("status", sa.String()),
        sa.Column("report", sa.String()),
    )


def downgrade() -> None:
    op.drop_table("report")
