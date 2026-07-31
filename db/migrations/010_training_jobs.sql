-- 31/07/2026 : bac a sable pedagogique, Phase 3 - table de suivi des
-- entrainements asynchrones (LSTM, puis GRU/Transformer plus tard). Voir
-- backend/app/domains/analysis_lab/db_models.py::TrainingJob et docs/STACK.md.
-- Seule table ecrite par ce domaine (le reste est strictement lecture seule).

CREATE TABLE IF NOT EXISTS training_jobs (
    id UUID PRIMARY KEY,
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    model_name VARCHAR(30) NOT NULL,
    horizon VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    result JSONB,
    error_message VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_training_jobs_asset_id ON training_jobs (asset_id);
