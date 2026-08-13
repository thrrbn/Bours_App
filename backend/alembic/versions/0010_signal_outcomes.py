"""signal_outcomes (scorecard de fiabilite reelle des signaux)

13/08/2026 : voir backend/app/domains/signal_reliability/models.py pour la
discussion complete - une ligne par signal reel evalue une fois son horizon
ecoule (job quotidien), alimente le scorecard de precision par horizon/
fenetre glissante (distinct du backtest a la demande, domaine backtests).

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "signal_outcomes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "signal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("signals.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("horizon", sa.String(20), nullable=False),
        sa.Column("signal_computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("final_signal", sa.String(30), nullable=False),
        sa.Column("forward_return", sa.Numeric(10, 6), nullable=False),
        sa.Column("was_correct", sa.Boolean(), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_signal_outcomes_signal_id", "signal_outcomes", ["signal_id"], unique=True)
    op.create_index("ix_signal_outcomes_asset_id", "signal_outcomes", ["asset_id"])
    op.create_index("ix_signal_outcomes_horizon", "signal_outcomes", ["horizon"])
    op.create_index("ix_signal_outcomes_signal_computed_at", "signal_outcomes", ["signal_computed_at"])


def downgrade() -> None:
    op.drop_index("ix_signal_outcomes_signal_computed_at", table_name="signal_outcomes")
    op.drop_index("ix_signal_outcomes_horizon", table_name="signal_outcomes")
    op.drop_index("ix_signal_outcomes_asset_id", table_name="signal_outcomes")
    op.drop_index("ix_signal_outcomes_signal_id", table_name="signal_outcomes")
    op.drop_table("signal_outcomes")
