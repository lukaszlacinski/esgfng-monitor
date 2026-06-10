"""Create healthcheck_results table.

Revision ID: 20250610_0001
Revises:
Create Date: 2025-06-10

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20250610_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "healthcheck_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("target_name", sa.String(length=64), nullable=False),
        sa.Column("url", sa.String(length=512), nullable=False),
        sa.Column(
            "checked_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("http_status_code", sa.Integer(), nullable=True),
        sa.Column("time_namelookup", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("time_connect", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("time_appconnect", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("time_pretransfer", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column(
            "time_starttransfer",
            sa.Numeric(precision=12, scale=6),
            nullable=True,
        ),
        sa.Column("time_total", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_healthcheck_results_target_checked_at",
        "healthcheck_results",
        ["target_name", "checked_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_healthcheck_results_target_checked_at",
        table_name="healthcheck_results",
    )
    op.drop_table("healthcheck_results")
