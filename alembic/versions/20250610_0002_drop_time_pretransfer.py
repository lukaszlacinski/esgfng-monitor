"""Drop time_pretransfer column.

Revision ID: 20250610_0002
Revises: 20250610_0001
Create Date: 2025-06-10

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20250610_0002"
down_revision: Union[str, Sequence[str], None] = "20250610_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("healthcheck_results", "time_pretransfer")


def downgrade() -> None:
    op.add_column(
        "healthcheck_results",
        sa.Column("time_pretransfer", sa.Numeric(precision=12, scale=6), nullable=True),
    )
