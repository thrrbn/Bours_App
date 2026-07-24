-- Etape 17 : frais et slippage dans le portefeuille virtuel de simulation.
-- Sans ces colonnes, la simulation surestimait la performance en ignorant
-- les couts reels d'un ordre (commission fixe + slippage defavorable).

ALTER TABLE portfolio_transactions ADD COLUMN IF NOT EXISTS quoted_price NUMERIC(18, 6);
ALTER TABLE portfolio_transactions ADD COLUMN IF NOT EXISTS commission NUMERIC(18, 2) NOT NULL DEFAULT 0;
ALTER TABLE portfolio_transactions ADD COLUMN IF NOT EXISTS slippage_amount NUMERIC(18, 2) NOT NULL DEFAULT 0;

-- Backfill des transactions existantes (creees avant l'Etape 17) : on
-- considere que leur "price" execute est aussi le cours cote, puisqu'a
-- l'epoque aucun slippage n'etait simule.
UPDATE portfolio_transactions SET quoted_price = price WHERE quoted_price IS NULL;
