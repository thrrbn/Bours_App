import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    engine_version: Mapped[str] = mapped_column(String(50), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    asset_scope: Mapped[dict | None] = mapped_column(JSONB)
    # 13/08/2026 : "manual" (defaut, "Lancer le test" avec parametres choisis
    # par l'utilisateur) ou "scheduled_strategy_eval" (job hebdomadaire,
    # parametres par defaut, voir jobs/evaluate_strategies_job.py) - permet
    # au scorecard de fiabilite par strategie de n'agreger QUE des runs
    # comparables entre eux (memes parametres, cadence reguliere), sans
    # melanger avec les tests ad-hoc de l'utilisateur.
    run_kind: Mapped[str] = mapped_column(String(20), nullable=False, server_default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    backtest_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("backtest_runs.id", ondelete="CASCADE"), index=True
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"))
    horizon: Mapped[str] = mapped_column(String(20), nullable=False)
    precision: Mapped[float | None] = mapped_column(Numeric(5, 4))
    win_rate: Mapped[float | None] = mapped_column(Numeric(5, 4))
    false_positive_rate: Mapped[float | None] = mapped_column(Numeric(5, 4))
    max_drawdown: Mapped[float | None] = mapped_column(Numeric(6, 4))
    signal_count: Mapped[int] = mapped_column(Integer, default=0)
    # Etape 18 : metriques financieres complementaires (voir backtests/service.py
    # pour les definitions et simplifications assumees).
    sharpe_ratio: Mapped[float | None] = mapped_column(Numeric(10, 4))
    calmar_ratio: Mapped[float | None] = mapped_column(Numeric(10, 4))
    profit_factor: Mapped[float | None] = mapped_column(Numeric(10, 4))
    avg_risk_reward: Mapped[float | None] = mapped_column(Numeric(10, 4))
    # 31/07/2026 : integration de backtesting.py comme second moteur (voir
    # backtests/kernc_engine.py) - cohabite dans les MEMES tables que le
    # moteur interne (evaluate_signals) pour comparaison directe. strategy_name
    # distingue "internal_rules" (moteur historique, toujours pose explicitement
    # par router.py) de "signal_replay"/"sma_cross"/"buy_and_hold" (nouveau
    # moteur). extra_metrics stocke les statistiques riches de backtesting.py
    # qui n'ont pas d'equivalent typé ici (Sortino, Exposure Time, SQN,
    # Best/Worst Trade...), sans avoir a migrer une colonne par metrique.
    strategy_name: Mapped[str | None] = mapped_column(String(50))
    extra_metrics: Mapped[dict | None] = mapped_column(JSONB)
    # 01/08/2026 : graphique interactif natif de backtesting.py (bt.plot() -
    # chandeliers + courbe de capital + marqueurs de trades), genere en HTML
    # standalone au moment du run (voir kernc_engine.py::_render_plot_html)
    # et stocke tel quel - uniquement rempli pour le moteur backtesting.py
    # (jamais pour "internal_rules", qui n'a pas d'equivalent). NULL pour
    # tous les runs anterieurs a cet ajout (pas de reconstruction retroactive
    # possible sans rejouer le backtest, voir discussion avec l'utilisateur).
    plot_html: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
