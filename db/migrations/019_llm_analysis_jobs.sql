-- 16/08/2026 : analyste IA (LLM local, instance locale PC/Mac uniquement -
-- voir docs/20-instance-locale-pc-mac.md et backend/app/domains/llm_analyst/
-- db_models.py::AnalysisJob). Meme raisonnement que training_jobs
-- (010_training_jobs.sql, Phase 3) : un appel a un LLM local prend jusqu'a
-- plusieurs minutes, trop long pour un appel HTTP synchrone.
--
-- Reste vide en pratique sur une instance ou ENABLE_LLM_ANALYST n'est pas
-- explicitement mis a true (jamais le cas sur le NAS deploye).

CREATE TABLE IF NOT EXISTS llm_analysis_jobs (
    id UUID PRIMARY KEY,
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    strategy_name VARCHAR(30) NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    model_name VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    result JSONB,
    error_message VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_llm_analysis_jobs_asset_id ON llm_analysis_jobs (asset_id);
