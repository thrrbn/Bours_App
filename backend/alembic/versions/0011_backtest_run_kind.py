"""backtest_runs.run_kind (manual vs scheduled_strategy_eval)

13/08/2026 : voir backend/app/domains/backtests/models.py et
app/jobs/evaluate_strategies_job.py - distingue les runs crees par
l'utilisateur ("Lancer le test", parametres personnalises) des runs generes
automatiquement chaque semaine (parametres par defaut, sur les positions du
portefeuille virtuel) pour alimenter le scorecard de fiabilite par strategie
- sans cette distinction, l'agregation du scorecard melangerait des runs a
parametres tres differents et perdrait tout son sens.

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "backtest_runs", sa.Column("run_kind", sa.String(20), nullable=False, server_default="manual")
    )
    op.create_index("ix_backtest_runs_run_kind", "backtest_runs", ["run_kind"])


def downgrade() -> None:
    op.drop_index("ix_backtest_runs_run_kind", table_name="backtest_runs")
    op.drop_column("backtest_runs", "run_kind")
