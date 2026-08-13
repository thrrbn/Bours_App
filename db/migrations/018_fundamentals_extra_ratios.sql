-- 13/08/2026 : ratios complementaires de la fiche titre (ROE, dette/capitaux
-- propres, marge nette, P/B, VE/EBITDA) - demande explicite de l'utilisateur.
-- Voir backend/app/domains/assets/fundamentals_models.py.

ALTER TABLE asset_fundamentals ADD COLUMN IF NOT EXISTS return_on_equity DOUBLE PRECISION;
ALTER TABLE asset_fundamentals ADD COLUMN IF NOT EXISTS debt_to_equity DOUBLE PRECISION;
ALTER TABLE asset_fundamentals ADD COLUMN IF NOT EXISTS profit_margin DOUBLE PRECISION;
ALTER TABLE asset_fundamentals ADD COLUMN IF NOT EXISTS price_to_book DOUBLE PRECISION;
ALTER TABLE asset_fundamentals ADD COLUMN IF NOT EXISTS ev_to_ebitda DOUBLE PRECISION;
