-- 31/07/2026 : historique des dividendes + suivi des couts complementaires
-- du portefeuille virtuel (TOB belge, credit de dividendes). Voir
-- backend/app/domains/market_data/models.py::Dividend et docs/STACK.md.

CREATE TABLE IF NOT EXISTS dividends (
    id BIGSERIAL PRIMARY KEY,
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    ex_date DATE NOT NULL,
    amount_per_share NUMERIC(18, 6) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_dividend_asset_date UNIQUE (asset_id, ex_date)
);
CREATE INDEX IF NOT EXISTS ix_dividends_asset_id ON dividends (asset_id);

ALTER TABLE portfolio_positions ADD COLUMN IF NOT EXISTS dividends_credited_until DATE;
ALTER TABLE portfolio_transactions ADD COLUMN IF NOT EXISTS tob_amount NUMERIC(18, 2) NOT NULL DEFAULT 0;
