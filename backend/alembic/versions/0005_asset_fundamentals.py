"""asset_fundamentals table (fiche titre - fondamentaux Yahoo Finance)

31/07/2026 : nouvelle "fiche titre" par actif (secteur/industrie,
capitalisation, PER trailing/forward, rendement du dividende, fourchette 52
semaines, beta, resume d'activite) - alimente un nouvel onglet sur la page
actif (frontend/src/components/FundamentalsPanel.vue). Meme convention
qu'analyst_consensus (0001_baseline_schema.py) : UNE ligne par actif,
rafraichie a la demande (voir POST /assets/{id}/fundamentals/refresh),
jamais un historique - Yahoo ne donne de toute facon que la derniere valeur
connue pour ces champs.

A appliquer sur une base EXISTANTE via `docker compose exec backend alembic
upgrade head` (le fichier db/migrations/011_asset_fundamentals.sql ne
bootstrape qu'un volume Postgres neuf).

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-31

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "asset_fundamentals",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("asset_id", sa.UUID(), nullable=False),
        sa.Column("sector", sa.String(length=100), nullable=True),
        sa.Column("industry", sa.String(length=150), nullable=True),
        sa.Column("market_cap", sa.BigInteger(), nullable=True),
        sa.Column("trailing_pe", sa.Float(), nullable=True),
        sa.Column("forward_pe", sa.Float(), nullable=True),
        sa.Column("dividend_yield", sa.Float(), nullable=True),
        sa.Column("week52_low", sa.Float(), nullable=True),
        sa.Column("week52_high", sa.Float(), nullable=True),
        sa.Column("beta", sa.Float(), nullable=True),
        sa.Column("business_summary", sa.Text(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", name="uq_asset_fundamentals_asset_id"),
    )
    op.create_index(op.f("ix_asset_fundamentals_asset_id"), "asset_fundamentals", ["asset_id"], unique=True)
    op.create_index(op.f("ix_asset_fundamentals_sector"), "asset_fundamentals", ["sector"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_asset_fundamentals_sector"), table_name="asset_fundamentals")
    op.drop_index(op.f("ix_asset_fundamentals_asset_id"), table_name="asset_fundamentals")
    op.drop_table("asset_fundamentals")
