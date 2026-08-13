-- 13/08/2026 : scorecard de fiabilite reelle des signaux (distinct du
-- backtest a la demande) - une ligne par signal reel evalue une fois son
-- horizon ecoule (job quotidien). Voir
-- backend/app/domains/signal_reliability/models.py.

CREATE TABLE IF NOT EXISTS signal_outcomes (
    id UUID PRIMARY KEY,
    signal_id UUID NOT NULL UNIQUE REFERENCES signals(id) ON DELETE CASCADE,
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    horizon VARCHAR(20) NOT NULL,
    signal_computed_at TIMESTAMPTZ NOT NULL,
    final_signal VARCHAR(30) NOT NULL,
    forward_return NUMERIC(10, 6) NOT NULL,
    was_correct BOOLEAN NOT NULL,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_signal_outcomes_asset_id ON signal_outcomes (asset_id);
CREATE INDEX IF NOT EXISTS ix_signal_outcomes_horizon ON signal_outcomes (horizon);
CREATE INDEX IF NOT EXISTS ix_signal_outcomes_signal_computed_at ON signal_outcomes (signal_computed_at);
