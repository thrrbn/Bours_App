-- 01/08/2026 : page "Marche" - indices (FR/BE/Europe/US, en direct) + plus
-- fortes hausses/baisses parmi les actifs deja suivis (FR/US), rafraichie
-- 3x/jour (7h, 12h, 17h). Voir backend/app/domains/market_overview/models.py.

CREATE TABLE IF NOT EXISTS market_snapshots (
    id UUID PRIMARY KEY,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    indices JSONB NOT NULL,
    movers JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_market_snapshots_captured_at ON market_snapshots (captured_at);
