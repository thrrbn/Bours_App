"""dividends table + portfolio cost tracking (dividendes, TOB)

31/07/2026 : voir docs/STACK.md pour le recit complet.
- Nouvelle table `dividends` (historique des dividendes par actif, ingere via
  yfinance - voir market_data/providers/yahoo_finance.py::fetch_dividends).
- `portfolio_positions.dividends_credited_until` : derniere date de
  detachement deja creditee pour cette position (evite le double-credit).
- `portfolio_transactions.tob_amount` : taxe belge sur les operations de
  bourse, tracee separement de la commission/du slippage pour un detail de
  cout transparent (objectif pedagogique).

A appliquer sur une base EXISTANTE via `docker compose exec backend alembic
upgrade head` (les fichiers db/migrations/*.sql, dont le nouveau
009_dividends_and_tob.sql, ne bootstrapent qu'un volume Postgres neuf).

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-31

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dividends",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("asset_id", sa.UUID(), nullable=False),
        sa.Column("ex_date", sa.Date(), nullable=False),
        sa.Column("amount_per_share", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "ex_date", name="uq_dividend_asset_date"),
    )
    op.create_index(op.f("ix_dividends_asset_id"), "dividends", ["asset_id"], unique=False)

    op.add_column("portfolio_positions", sa.Column("dividends_credited_until", sa.Date(), nullable=True))
    op.add_column(
        "portfolio_transactions",
        sa.Column("tob_amount", sa.Numeric(precision=18, scale=2), server_default=sa.text("0"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("portfolio_transactions", "tob_amount")
    op.drop_column("portfolio_positions", "dividends_credited_until")
    op.drop_index(op.f("ix_dividends_asset_id"), table_name="dividends")
    op.drop_table("dividends")
