import uuid
from datetime import date, datetime

from pydantic import BaseModel


class SmaParamsOverride(BaseModel):
    """
    Laboratoire de parametres (31/07/2026, voir kernc_engine.py) : fenetres
    des moyennes mobiles pour la strategie sma_cross, testables par run sans
    toucher au code. Defauts identiques au comportement historique (10/20).
    """

    n1: int = 10
    n2: int = 20


class DecisionParamsOverride(BaseModel):
    """
    Laboratoire de parametres (31/07/2026, voir kernc_engine.py et
    signals/models_ml/baseline_rules.py::DecisionParams) : seuils et
    ponderation de la fonction de decision utilisee par signal_replay pour
    reclassifier les scores bruts DEJA stockes. Defauts identiques au moteur
    de signal reel (DEFAULT_DECISION_PARAMS) - ne jamais utiliser ce schema
    pour modifier le moteur reel, uniquement pour comparer des variantes en
    backtest (decision produit explicite, voir docs/STACK.md).
    """

    technical_weight: float = 0.5
    news_weight: float = 0.5
    buy_threshold: float = 70.0
    watch_threshold: float = 55.0
    caution_threshold: float = 45.0
    sell_threshold: float = 30.0
    buy_max_risk: float = 50.0
    sell_min_risk: float = 60.0
    min_confidence: float = 30.0


class RsiParamsOverride(BaseModel):
    """
    Laboratoire de parametres (13/08/2026, voir kernc_engine.py::RsiStrategy) :
    periode du RSI et seuils de survente/surachat, testables par run sans
    toucher au code. Defauts identiques a la convention usuelle (14/30/70).
    """

    period: int = 14
    oversold: float = 30.0
    overbought: float = 70.0


class MacdParamsOverride(BaseModel):
    """
    Laboratoire de parametres (13/08/2026, voir kernc_engine.py::MacdStrategy) :
    fenetres rapide/lente de la ligne MACD et fenetre de la ligne de signal.
    Defauts identiques a la convention usuelle (12/26/9).
    """

    fast: int = 12
    slow: int = 26
    signal: int = 9


class BollingerParamsOverride(BaseModel):
    """
    Laboratoire de parametres (13/08/2026, voir kernc_engine.py::BollingerStrategy) :
    periode de la moyenne mobile et largeur des bandes en ecarts-types.
    Defauts identiques a la convention usuelle (20/2.0).
    """

    period: int = 20
    num_std: float = 2.0


class BacktestRunCreate(BaseModel):
    """
    01/08/2026 : decision_params optionnel (voir DecisionParamsOverride
    ci-dessus et service.py::run_backtest_for_asset) - laboratoire de
    parametres etendu au moteur interne, meme principe que
    BacktestKerncRunCreate ci-dessous. Omis, comportement identique a avant
    (final_signal deja stocke, inchange).
    """

    engine_version: str
    period_start: date
    period_end: date
    asset_ids: list[uuid.UUID]
    decision_params: DecisionParamsOverride | None = None


class BacktestKerncRunCreate(BaseModel):
    """
    Bug reel trouve le 31/07/2026 : POST /run-kernc reutilisait BacktestRunCreate,
    qui exige `engine_version` - mais ce champ n'a pas de sens cote client pour
    ce moteur : `engine_version` est determine automatiquement par le code
    (f"backtesting.py-{version installee}", voir router.py), le client n'a pas
    a le fournir. Schema dedie, sans ce champ.

    sma_params / decision_params (31/07/2026) et rsi_params / macd_params /
    bollinger_params (13/08/2026) : tous optionnels, permettent de tester des
    variantes de parametres (voir les schemas *Override ci-dessus) - omis, le
    comportement est identique aux defauts de chaque strategie.
    """

    period_start: date
    period_end: date
    asset_ids: list[uuid.UUID]
    sma_params: SmaParamsOverride | None = None
    decision_params: DecisionParamsOverride | None = None
    rsi_params: RsiParamsOverride | None = None
    macd_params: MacdParamsOverride | None = None
    bollinger_params: BollingerParamsOverride | None = None


class BacktestResultRead(BaseModel):
    asset_id: uuid.UUID
    horizon: str
    precision: float | None
    win_rate: float | None
    false_positive_rate: float | None
    max_drawdown: float | None
    signal_count: int
    sharpe_ratio: float | None = None
    calmar_ratio: float | None = None
    profit_factor: float | None = None
    avg_risk_reward: float | None = None
    # 31/07/2026 : integration backtesting.py (voir kernc_engine.py).
    # strategy_name distingue "internal_rules" du nouveau moteur ; extra_metrics
    # porte les statistiques riches de backtesting.py sans equivalent type
    # ci-dessus (Sortino, Exposure Time, SQN, Best/Worst Trade...).
    strategy_name: str | None = None
    extra_metrics: dict | None = None
    # 01/08/2026 : HTML standalone du graphique interactif bt.plot() (voir
    # kernc_engine.py::_render_plot_html) - None pour "internal_rules" et
    # pour tout run anterieur a cet ajout.
    plot_html: str | None = None


class StrategyWindowStats(BaseModel):
    count: int
    avg_win_rate: float | None
    avg_return_pct: float | None


class StrategyScorecardRow(BaseModel):
    """
    13/08/2026 (scorecard de fiabilite par strategie, voir
    jobs/evaluate_strategies_job.py) : une ligne = une strategie (+horizon
    pour signal_replay/internal_rules, "n/a" sinon - meme convention que
    ParamsLabPanel.vue::resultKey), avec ses stats agregees sur chaque
    fenetre glissante (voir service.py::SCORECARD_WINDOWS).
    """

    strategy_name: str
    horizon: str
    windows: dict[str, StrategyWindowStats]


class StrategyScorecardRead(BaseModel):
    results: list[StrategyScorecardRow]
    last_evaluated_at: datetime | None
    disclaimer: str = (
        "Moyennes calculees UNIQUEMENT sur les runs automatiques hebdomadaires (parametres par defaut et "
        "profils predefinis prudent/agressif, positions du portefeuille virtuel) - jamais sur tes tests "
        "manuels. Chaque profil est reevalue chaque semaine sur les donnees les plus recentes, jamais "
        "optimise une seule fois sur une periode deja connue. Mesure la performance passee de chaque "
        "strategie sur les actifs suivis, jamais une prediction ni une recommandation."
    )
