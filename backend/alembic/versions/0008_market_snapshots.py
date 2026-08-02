"""market_snapshots table (page Marche - indices + top hausses/baisses)

01/08/2026 : voir backend/app/domains/market_overview/models.py pour la
discussion complete (JSONB, une ligne par rafraichissement).

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-01

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "market_snapshots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("indices", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("movers", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_market_snapshots_captured_at"), "market_snapshots", ["captured_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_market_snapshots_captured_at"), table_name="market_snapshots")
    op.drop_table("market_snapshots")
