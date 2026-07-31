import uuid
from datetime import date

from pydantic import BaseModel


class BacktestRunCreate(BaseModel):
    engine_version: str
    period_start: date
    period_end: date
    asset_ids: list[uuid.UUID]


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


class BacktestKerncRunCreate(BaseModel):
    """
    Bug reel trouve le 31/07/2026 : POST /run-kernc reutilisait BacktestRunCreate,
    qui exige `engine_version` - mais ce champ n'a pas de sens cote client pour
    ce moteur : `engine_version` est determine automatiquement par le code
    (f"backtesting.py-{version installee}", voir router.py), le client n'a pas
    a le fournir. Schema dedie, sans ce champ.

    sma_params / decision_params (31/07/2026) : optionnels, permettent de
    tester des variantes de parametres (voir SmaParamsOverride/
    DecisionParamsOverride ci-dessus) - omis, le comportement est identique
    a avant (fenetres SMA 10/20, seuils de decision par defaut).
    """

    period_start: date
    period_end: date
    asset_ids: list[uuid.UUID]
    sma_params: SmaParamsOverride | None = None
    decision_params: DecisionParamsOverride | None = None


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
