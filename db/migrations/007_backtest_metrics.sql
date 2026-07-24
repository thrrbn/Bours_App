-- Etape 18 : metriques financieres complementaires du backtesting
-- (Sharpe, Calmar, profit factor, R:R moyen). Voir
-- backend/app/domains/backtests/service.py pour les definitions.

ALTER TABLE backtest_results ADD COLUMN IF NOT EXISTS sharpe_ratio NUMERIC(10, 4);
ALTER TABLE backtest_results ADD COLUMN IF NOT EXISTS calmar_ratio NUMERIC(10, 4);
ALTER TABLE backtest_results ADD COLUMN IF NOT EXISTS profit_factor NUMERIC(10, 4);
ALTER TABLE backtest_results ADD COLUMN IF NOT EXISTS avg_risk_reward NUMERIC(10, 4);
