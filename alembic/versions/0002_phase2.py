"""phase-2 — answer_runs.result_columns_json / result_rows_json / day

Adds three columns needed by the phase-2 endpoints (/api/history,
/api/usage/by-day, /api/ask/{id}/csv, /api/ask/{id}/anomalies).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("answer_runs") as batch_op:
        batch_op.add_column(
            sa.Column(
                "result_columns_json",
                sa.Text(),
                nullable=False,
                server_default="[]",
            )
        )
        batch_op.add_column(
            sa.Column(
                "result_rows_json",
                sa.Text(),
                nullable=False,
                server_default="[]",
            )
        )
        batch_op.add_column(
            sa.Column(
                "day",
                sa.String(),
                nullable=False,
                server_default="1970-01-01",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("answer_runs") as batch_op:
        batch_op.drop_column("day")
        batch_op.drop_column("result_rows_json")
        batch_op.drop_column("result_columns_json")
