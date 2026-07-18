-- ============================================================================
-- Migration 005 : consensus d'analystes externes (Yahoo Finance)
--   Get-Content db/migrations/005_analyst_consensus.sql | docker compose exec -T db psql -U bourse_user -d bourse
-- ============================================================================

CREATE TABLE IF NOT EXISTS analyst_consensus (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id            UUID NOT NULL UNIQUE REFERENCES assets(id) ON DELETE CASCADE,
    strong_buy          INTEGER NOT NULL,
    buy                 INTEGER NOT NULL,
    hold                INTEGER NOT NULL,
    sell                INTEGER NOT NULL,
    strong_sell         INTEGER NOT NULL,
    consensus_score     DOUBLE PRECISION NOT NULL,
    consensus_label     VARCHAR(20) NOT NULL,
    fetched_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_analyst_consensus_asset ON analyst_consensus (asset_id);
