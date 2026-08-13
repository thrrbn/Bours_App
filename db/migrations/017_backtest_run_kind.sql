-- 13/08/2026 : distingue les runs de backtest crees par l'utilisateur
-- ("manual", parametres personnalises) des runs generes automatiquement
-- chaque semaine ("scheduled_strategy_eval", parametres par defaut, sur le
-- portefeuille virtuel) - alimente le scorecard de fiabilite par strategie.
-- Voir backend/app/domains/backtests/models.py et
-- app/jobs/evaluate_strategies_job.py.

ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS run_kind VARCHAR(20) NOT NULL DEFAULT 'manual';
CREATE INDEX IF NOT EXISTS ix_backtest_runs_run_kind ON backtest_runs (run_kind);
