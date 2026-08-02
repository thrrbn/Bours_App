"""backtest_results.plot_html (graphique interactif backtesting.py)

01/08/2026 : voir backend/app/domains/backtests/models.py pour la
discussion complete (NULL pour les runs anterieurs a cet ajout).

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-01

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("backtest_results", sa.Column("plot_html", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("backtest_results", "plot_html")
