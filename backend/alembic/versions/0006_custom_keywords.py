"""custom_keywords table (mots-cles personnalises, briefing quotidien)

31/07/2026 : liste GLOBALE de mots-cles/opportunites choisis par l'utilisateur
(voir news/custom_keywords_models.py), en plus du lexique fixe pondere
(nlp/lexicon.py) - fusionnee au moment de l'ingestion des news
(news/service.py::ingest_and_score) et de la synthese du briefing quotidien
(notifications/briefing_service.py).

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-31

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "custom_keywords",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("keyword", sa.String(length=100), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("horizon_impact", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("keyword", name="uq_custom_keywords_keyword"),
    )


def downgrade() -> None:
    op.drop_table("custom_keywords")
