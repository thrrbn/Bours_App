"""widen backtest_runs.run_kind to 30 chars

Bug reel trouve le 14/08/2026 en testant manuellement le job planifie
evaluate_strategies_job : String(20) etait trop court pour la valeur
"scheduled_strategy_eval" (23 caracteres) qu'il ecrit dans run_kind -
StringDataRightTruncationError des le premier create_run(), a chaque
execution. Voir backend/app/domains/backtests/models.py.

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-14 09:56:12.622881

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0013'
down_revision: Union[str, None] = '0012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'backtest_runs', 'run_kind',
        existing_type=sa.VARCHAR(length=20),
        type_=sa.String(length=30),
        existing_nullable=False,
        existing_server_default=sa.text("'manual'::character varying"),
    )


def downgrade() -> None:
    op.alter_column(
        'backtest_runs', 'run_kind',
        existing_type=sa.String(length=30),
        type_=sa.VARCHAR(length=20),
        existing_nullable=False,
        existing_server_default=sa.text("'manual'::character varying"),
    )
