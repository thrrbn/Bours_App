-- 31/07/2026 : fiche titre - fondamentaux Yahoo Finance (secteur/industrie,
-- capitalisation, PER, rendement du dividende, fourchette 52 semaines, beta,
-- resume d'activite). Voir backend/app/domains/assets/fundamentals_models.py
-- et docs/STACK.md. Une seule ligne par actif, rafraichie a la demande.

CREATE TABLE IF NOT EXISTS asset_fundamentals (
    id UUID PRIMARY KEY,
    asset_id UUID NOT NULL UNIQUE REFERENCES assets(id) ON DELETE CASCADE,
    sector VARCHAR(100),
    industry VARCHAR(150),
    market_cap BIGINT,
    trailing_pe DOUBLE PRECISION,
    forward_pe DOUBLE PRECISION,
    dividend_yield DOUBLE PRECISION,
    week52_low DOUBLE PRECISION,
    week52_high DOUBLE PRECISION,
    beta DOUBLE PRECISION,
    business_summary TEXT,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_asset_fundamentals_asset_id ON asset_fundamentals (asset_id);
CREATE INDEX IF NOT EXISTS ix_asset_fundamentals_sector ON asset_fundamentals (sector);
