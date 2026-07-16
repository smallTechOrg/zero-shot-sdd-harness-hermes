"""initial — AnswerRun + CctnsTable

Revision ID: 0001
Revises:
Create Date: 2026-07-16 19:00:00

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "answer_runs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("request_id", sa.String(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("sql_template", sa.Text(), nullable=False, server_default=""),
        sa.Column("sql_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )
    op.create_table(
        "cctns_tables",
        sa.Column("name", sa.String(), primary_key=True),
        sa.Column("schema_name", sa.String(), nullable=False, server_default="cctns_mirror"),
        sa.Column("columns_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("version", sa.String(), nullable=False, server_default="v1"),
        sa.Column("captured_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("answer_runs")
    op.drop_table("cctns_tables")
