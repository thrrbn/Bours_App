-- 31/07/2026 : integration de backtesting.py (kernc/backtesting.py) comme
-- second moteur de backtest, cohabitant avec le moteur interne dans les
-- memes tables. Voir backend/app/domains/backtests/kernc_engine.py.

ALTER TABLE backtest_results ADD COLUMN IF NOT EXISTS strategy_name VARCHAR(50);
ALTER TABLE backtest_results ADD COLUMN IF NOT EXISTS extra_metrics JSONB;
