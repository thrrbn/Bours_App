-- 31/07/2026 : mots-cles personnalises (liste globale, en plus du lexique
-- fixe nlp/lexicon.py) - voir backend/app/domains/news/custom_keywords_models.py.

CREATE TABLE IF NOT EXISTS custom_keywords (
    id UUID PRIMARY KEY,
    keyword VARCHAR(100) NOT NULL UNIQUE,
    weight DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    horizon_impact VARCHAR(20) NOT NULL DEFAULT 'medium',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
