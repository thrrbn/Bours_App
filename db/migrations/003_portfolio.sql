-- ============================================================================
-- Migration 003 : portefeuille virtuel de simulation (Etape 12)
-- A appliquer manuellement sur la base existante, comme la migration 002 :
--   Get-Content db/migrations/003_portfolio.sql | docker compose exec -T db psql -U bourse_user -d bourse
-- ============================================================================

CREATE TABLE IF NOT EXISTS portfolio_state (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cash_balance    NUMERIC(18, 2) NOT NULL,
    starting_cash   NUMERIC(18, 2) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS portfolio_positions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id        UUID NOT NULL UNIQUE REFERENCES assets(id) ON DELETE CASCADE,
    quantity        NUMERIC(18, 6) NOT NULL,
    avg_cost        NUMERIC(18, 6) NOT NULL,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_portfolio_positions_asset ON portfolio_positions (asset_id);

CREATE TABLE IF NOT EXISTS portfolio_transactions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id        UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    side            VARCHAR(10) NOT NULL,           -- 'buy' | 'sell'
    quantity        NUMERIC(18, 6) NOT NULL,
    price           NUMERIC(18, 6) NOT NULL,
    total_amount    NUMERIC(18, 2) NOT NULL,
    realized_pnl    NUMERIC(18, 2),
    price_date      DATE NOT NULL,
    executed_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_portfolio_transactions_asset ON portfolio_transactions (asset_id);
