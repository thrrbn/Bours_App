-- ============================================================================
-- Migration 002 : watchlist + notifications (Etape 11 / 11bis)
-- Ce fichier N'EST PAS execute automatiquement (docker-entrypoint-initdb.d ne
-- rejoue les scripts que sur un volume vide, or ta base contient deja des
-- donnees). A appliquer manuellement une seule fois sur la base existante,
-- par exemple :
--   docker compose exec -T db psql -U bourse_user -d bourse < db/migrations/002_watchlist_notifications.sql
-- (remplace bourse_user si tu as change POSTGRES_USER dans ton .env)
-- ============================================================================

-- Watchlist : actifs suivis (mono-utilisateur en V1, voir backend/app/domains/watchlist/models.py)
CREATE TABLE IF NOT EXISTS watchlist_items (
    id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id           UUID NOT NULL UNIQUE REFERENCES assets(id) ON DELETE CASCADE,
    notify_on_change   BOOLEAN NOT NULL DEFAULT TRUE,
    added_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_watchlist_items_asset ON watchlist_items (asset_id);

-- Notifications : dernier signal notifie par actif/horizon, pour ne notifier
-- que sur un changement (voir backend/app/domains/notifications/models.py)
CREATE TABLE IF NOT EXISTS notification_states (
    id                     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id               UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    horizon                VARCHAR(20) NOT NULL,
    last_notified_signal   VARCHAR(30) NOT NULL,
    last_notified_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (asset_id, horizon)
);
