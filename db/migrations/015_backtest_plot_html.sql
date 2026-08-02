-- 01/08/2026 : graphique interactif backtesting.py (bt.plot()), stocke en
-- HTML standalone. Voir backend/app/domains/backtests/models.py.

ALTER TABLE backtest_results ADD COLUMN IF NOT EXISTS plot_html TEXT;
