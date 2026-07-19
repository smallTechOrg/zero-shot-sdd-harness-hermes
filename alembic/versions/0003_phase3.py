"""phase-3 — answer_runs.timeline_json

Phase-3 structured observability persists the per-node timing list so
``/api/runs/{run_id}/timeline`` can serve it read-only without re-running
the run.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("answer_runs") as batch_op:
        batch_op.add_column(
            sa.Column(
                "timeline_json",
                sa.Text(),
                nullable=False,
                server_default="[]",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("answer_runs") as batch_op:
        batch_op.drop_column("timeline_json")
