-- 31/07/2026 : suivi du dernier signal inclus dans un briefing quotidien
-- reellement genere (portefeuille + watchlist) - voir
-- backend/app/domains/notifications/briefing_models.py. Distinct de
-- notification_states (002_watchlist_notifications.sql), qui appartient au
-- job de changement de signal sur la watchlist.

CREATE TABLE IF NOT EXISTS briefing_asset_states (
    id UUID PRIMARY KEY,
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    horizon VARCHAR(20) NOT NULL,
    last_signal VARCHAR(30) NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (asset_id, horizon)
);
CREATE INDEX IF NOT EXISTS ix_briefing_asset_states_asset_id ON briefing_asset_states (asset_id);
