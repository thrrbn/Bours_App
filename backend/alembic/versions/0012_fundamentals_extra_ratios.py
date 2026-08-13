"""asset_fundamentals - ratios complementaires (ROE, D/E, marge, P/B, EV/EBITDA)

13/08/2026 : voir backend/app/domains/assets/fundamentals_models.py -
enrichissement des fondamentaux + comparatif secteur (demande explicite de
l'utilisateur).

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("asset_fundamentals", sa.Column("return_on_equity", sa.Float(), nullable=True))
    op.add_column("asset_fundamentals", sa.Column("debt_to_equity", sa.Float(), nullable=True))
    op.add_column("asset_fundamentals", sa.Column("profit_margin", sa.Float(), nullable=True))
    op.add_column("asset_fundamentals", sa.Column("price_to_book", sa.Float(), nullable=True))
    op.add_column("asset_fundamentals", sa.Column("ev_to_ebitda", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("asset_fundamentals", "ev_to_ebitda")
    op.drop_column("asset_fundamentals", "price_to_book")
    op.drop_column("asset_fundamentals", "profit_margin")
    op.drop_column("asset_fundamentals", "debt_to_equity")
    op.drop_column("asset_fundamentals", "return_on_equity")
