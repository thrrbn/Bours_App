"""backtest_results: strategy_name + extra_metrics (integration backtesting.py)

Ajoute deux colonnes nullables a backtest_results pour accueillir le second
moteur de backtest (backtesting.py, voir app/domains/backtests/kernc_engine.py) :
- strategy_name : distingue "internal_rules" (moteur historique) de
  "signal_replay"/"sma_cross"/"buy_and_hold" (nouveau moteur).
- extra_metrics (JSONB) : statistiques riches de backtesting.py sans
  equivalent type ici (Sortino, Exposure Time, SQN, Best/Worst Trade...).

A appliquer sur une base EXISTANTE via `docker compose exec backend alembic
upgrade head` - contrairement a db/migrations/*.sql qui ne bootstrap qu'un
volume Postgres neuf (voir docker-compose.yml et le commentaire dans
0001_baseline_schema.py).

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-31

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("backtest_results", sa.Column("strategy_name", sa.String(length=50), nullable=True))
    op.add_column(
        "backtest_results",
        sa.Column("extra_metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("backtest_results", "extra_metrics")
    op.drop_column("backtest_results", "strategy_name")
