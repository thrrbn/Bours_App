"""llm_analysis_jobs table (analyste IA, instance locale PC/Mac)

16/08/2026 : voir docs/20-instance-locale-pc-mac.md pour le recit complet.
Un appel a un LLM local (Ollama) prend de quelques secondes a plusieurs
minutes - trop long pour un appel HTTP synchrone, meme raisonnement que
training_jobs (Phase 3, LSTM). `llm_analysis_jobs` porte le statut/resultat
d'une analyse lancee en tache de fond (voir jobs/llm_analysis_job.py),
interrogeable via polling (GET /api/v1/llm-analyst/jobs/{id}).

Cette table existe dans le meme schema que le reste de l'application (donc
aussi sur le NAS deploye une fois cette migration jouee la-bas) mais reste
vide en pratique : la feature est desactivee par defaut
(settings.enable_llm_analyst, voir router.py::require_enabled) - voir
docs/20 pour la discussion complete de ce choix.

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-16

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "llm_analysis_jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("asset_id", sa.UUID(), nullable=False),
        sa.Column("strategy_name", sa.String(length=30), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("model_name", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_llm_analysis_jobs_asset_id"), "llm_analysis_jobs", ["asset_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_llm_analysis_jobs_asset_id"), table_name="llm_analysis_jobs")
    op.drop_table("llm_analysis_jobs")
