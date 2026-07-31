"""training_jobs table (bac a sable pedagogique, Phase 3 - LSTM asynchrone)

31/07/2026 : voir docs/STACK.md pour le recit complet. Les modeles
sequentiels (LSTM, puis GRU/Transformer plus tard) prennent plusieurs
secondes a s'entrainer - trop long pour un appel HTTP synchrone comme
Random Forest/XGBoost/ARIMA/Prophet (Phases 1/2). `training_jobs` porte le
statut/resultat d'un entrainement lance en tache de fond (voir
jobs/deep_training_job.py), interrogeable via polling
(GET /analysis-lab/training-jobs/{id}).

Seule table ecrite par le domaine analysis_lab (voir
domains/analysis_lab/db_models.py pour la discussion de cette exception au
principe "lecture seule" du domaine) - ne touche jamais signals/portfolio/
backtest_results.

A appliquer sur une base EXISTANTE via `docker compose exec backend alembic
upgrade head` (le fichier db/migrations/010_training_jobs.sql ne bootstrape
qu'un volume Postgres neuf).

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-31

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "training_jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("asset_id", sa.UUID(), nullable=False),
        sa.Column("model_name", sa.String(length=30), nullable=False),
        sa.Column("horizon", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_training_jobs_asset_id"), "training_jobs", ["asset_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_training_jobs_asset_id"), table_name="training_jobs")
    op.drop_table("training_jobs")
