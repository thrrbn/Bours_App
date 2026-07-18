-- ============================================================================
-- Schéma PostgreSQL — Bourse Assistant
-- Ce fichier est le DDL de référence. En pratique, les tables sont créées et
-- versionnées par Alembic à partir des modèles SQLAlchemy (backend/app/domains/*/models.py).
-- Ce script sert de documentation lisible et de moyen de recréer la base sans Alembic
-- si besoin (ex. environnement de démo rapide).
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ----------------------------------------------------------------------------
-- Domaine: users
-- ----------------------------------------------------------------------------
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    is_admin        BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ----------------------------------------------------------------------------
-- Domaine: assets
-- ----------------------------------------------------------------------------
CREATE TABLE assets (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticker          VARCHAR(20) NOT NULL,
    name            VARCHAR(255) NOT NULL,
    market          VARCHAR(50) NOT NULL,      -- ex: 'EURONEXT_BRUSSELS', 'NASDAQ', 'NYSE'
    sector          VARCHAR(100),
    currency        VARCHAR(10) NOT NULL,       -- ex: 'EUR', 'USD'
    isin            VARCHAR(20),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (ticker, market)
);
CREATE INDEX idx_assets_ticker ON assets (ticker);
CREATE INDEX idx_assets_sector ON assets (sector);
CREATE INDEX idx_assets_market ON assets (market);

-- Watchlist : voir db/migrations/002_watchlist_notifications.sql
-- (watchlist_items, mono-utilisateur en V1 - pas de user_id, contrairement a
-- ce qui etait envisage ici a l'origine ; a revisiter si le multi-utilisateur
-- redevient necessaire)

-- ----------------------------------------------------------------------------
-- Domaine: market_data
-- ----------------------------------------------------------------------------
CREATE TABLE price_bars (
    id              BIGSERIAL PRIMARY KEY,
    asset_id        UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    trade_date      DATE NOT NULL,
    open            NUMERIC(18, 6) NOT NULL,
    high            NUMERIC(18, 6) NOT NULL,
    low             NUMERIC(18, 6) NOT NULL,
    close           NUMERIC(18, 6) NOT NULL,
    adjusted_close  NUMERIC(18, 6),
    volume          BIGINT NOT NULL,
    source          VARCHAR(50) NOT NULL DEFAULT 'yahoo_finance',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (asset_id, trade_date)
);
CREATE INDEX idx_price_bars_asset_date ON price_bars (asset_id, trade_date DESC);

CREATE TABLE technical_indicators (
    id              BIGSERIAL PRIMARY KEY,
    asset_id        UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    trade_date      DATE NOT NULL,
    sma_20          NUMERIC(18, 6),
    sma_50          NUMERIC(18, 6),
    sma_200         NUMERIC(18, 6),
    ema_12          NUMERIC(18, 6),
    ema_26          NUMERIC(18, 6),
    rsi_14          NUMERIC(6, 3),
    macd            NUMERIC(18, 6),
    macd_signal     NUMERIC(18, 6),
    bollinger_upper NUMERIC(18, 6),
    bollinger_lower NUMERIC(18, 6),
    volatility_20d  NUMERIC(10, 6),          -- écart-type des rendements sur 20 jours
    momentum_roc_20 NUMERIC(10, 6),          -- rate of change 20 jours
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (asset_id, trade_date)
);
CREATE INDEX idx_tech_ind_asset_date ON technical_indicators (asset_id, trade_date DESC);

-- ----------------------------------------------------------------------------
-- Domaine: news
-- ----------------------------------------------------------------------------
CREATE TABLE news_articles (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id            UUID REFERENCES assets(id) ON DELETE SET NULL,
    source              VARCHAR(100) NOT NULL,          -- ex: 'yahoo_rss', 'google_news_rss', 'benzinga'
    title               TEXT NOT NULL,
    url                 TEXT NOT NULL,
    published_at        TIMESTAMPTZ NOT NULL,
    raw_content         TEXT,
    sentiment_score     NUMERIC(5, 4),                   -- -1.0 (très négatif) à +1.0 (très positif)
    sentiment_method     VARCHAR(50),                     -- 'lexicon_v1', 'finbert', ...
    ingested_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (url)
);
CREATE INDEX idx_news_asset_published ON news_articles (asset_id, published_at DESC);

CREATE TABLE news_keyword_matches (
    id              BIGSERIAL PRIMARY KEY,
    article_id      UUID NOT NULL REFERENCES news_articles(id) ON DELETE CASCADE,
    keyword         VARCHAR(100) NOT NULL,       -- ex: 'profit warning', 'acquisition'
    weight          NUMERIC(5, 3) NOT NULL,       -- poids configuré pour ce mot-clé
    horizon_impact  VARCHAR(20) NOT NULL,         -- 'short', 'medium', 'long'
    occurrences     INTEGER NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_keyword_matches_article ON news_keyword_matches (article_id);

-- ----------------------------------------------------------------------------
-- Domaine: signals
-- ----------------------------------------------------------------------------
CREATE TABLE signals (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id            UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    horizon             VARCHAR(20) NOT NULL,       -- 'short', 'medium', 'long'
    computed_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    technical_score     NUMERIC(6, 3) NOT NULL,     -- 0-100
    news_score          NUMERIC(6, 3) NOT NULL,     -- 0-100
    risk_score          NUMERIC(6, 3) NOT NULL,     -- 0-100
    confidence_score    NUMERIC(6, 3) NOT NULL,     -- 0-100
    final_signal        VARCHAR(30) NOT NULL,        -- 'achat_speculatif' | 'surveillance' | 'neutre' | 'prudence' | 'vente_defensive'
    engine_version      VARCHAR(50) NOT NULL,         -- traçabilité: 'rules_v1', 'logistic_v1'...
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_signals_asset_horizon_date ON signals (asset_id, horizon, computed_at DESC);

CREATE TABLE signal_explanations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    signal_id       UUID NOT NULL REFERENCES signals(id) ON DELETE CASCADE,
    component       VARCHAR(50) NOT NULL,       -- 'technical', 'news', 'risk'
    contribution_pct NUMERIC(5, 2) NOT NULL,     -- poids relatif dans le score final
    text_explanation TEXT NOT NULL,               -- phrase lisible générée par template
    supporting_data  JSONB,                       -- ex: {"rsi_14": 28, "trend": "baissier"}
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_signal_explanations_signal ON signal_explanations (signal_id);

-- ----------------------------------------------------------------------------
-- Domaine: backtests
-- ----------------------------------------------------------------------------
CREATE TABLE backtest_runs (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    engine_version      VARCHAR(50) NOT NULL,
    period_start        DATE NOT NULL,
    period_end          DATE NOT NULL,
    asset_scope         JSONB,                       -- liste de tickers ou critère (secteur, marché)
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE backtest_results (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    backtest_run_id     UUID NOT NULL REFERENCES backtest_runs(id) ON DELETE CASCADE,
    asset_id            UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    horizon             VARCHAR(20) NOT NULL,
    precision           NUMERIC(5, 4),
    win_rate            NUMERIC(5, 4),
    false_positive_rate NUMERIC(5, 4),
    max_drawdown        NUMERIC(6, 4),
    signal_count        INTEGER NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_backtest_results_run ON backtest_results (backtest_run_id);

-- ----------------------------------------------------------------------------
-- Domaine: compliance (journal d'audit transverse)
-- ----------------------------------------------------------------------------
CREATE TABLE compliance_audit_log (
    id              BIGSERIAL PRIMARY KEY,
    entity_type     VARCHAR(50) NOT NULL,        -- 'signal', 'news_article'...
    entity_id       UUID NOT NULL,
    event           VARCHAR(100) NOT NULL,        -- 'signal_generated', 'disclaimer_shown'...
    details         JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_audit_log_entity ON compliance_audit_log (entity_type, entity_id);
