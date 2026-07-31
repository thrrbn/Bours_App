"""briefing_asset_states table (briefing quotidien portefeuille + watchlist)

31/07/2026 : suivi du dernier signal INCLUS dans un briefing reellement
genere (voir notifications/briefing_models.py pour la distinction avec
notification_states, deja utilisee par le job de changement de signal sur la
watchlist - 0001_baseline_schema.py). Permet au briefing quotidien de ne
mettre en avant que ce qui est NOUVEAU depuis le dernier envoi reel.

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-31

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "briefing_asset_states",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("asset_id", sa.UUID(), nullable=False),
        sa.Column("horizon", sa.String(length=20), nullable=False),
        sa.Column("last_signal", sa.String(length=30), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "horizon", name="uq_briefing_state_asset_horizon"),
    )
    op.create_index(op.f("ix_briefing_asset_states_asset_id"), "briefing_asset_states", ["asset_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_briefing_asset_states_asset_id"), table_name="briefing_asset_states")
    op.drop_table("briefing_asset_states")
