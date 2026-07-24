"""
Configuration centralisee de l'application.
Toutes les variables d'environnement transitent par cette classe unique
(Settings) - jamais de os.environ.get(...) dissemine dans le reste du code.

Adaptee au docker-compose fourni : la base est configuree via des variables
separees (DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME), pas via une URL
unique - c'est ce docker-compose.yml qui les injecte dans le conteneur
backend. `database_url` reste disponible comme propriete calculee, pour ne
rien changer dans database.py ni dans alembic/env.py.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"

    # --- Base de donnees (variables separees, alignees sur docker-compose.yml) ---
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "bourse_user"
    db_password: str = "bourse_pass"
    db_name: str = "bourse"

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    # --- Authentification ---
    jwt_secret_key: str = "changeme"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # --- Notifications email (Etape 11 - desactivees par defaut) ---
    mail_enabled: bool = False
    mail_server: str = "smtp.gmail.com"
    mail_port: int = 587
    mail_user: str | None = None
    mail_password: str | None = None
    mail_from: str | None = None
    # Destinataire des notifications (watchlist) - par defaut, on s'envoie a
    # soi-meme (mail_user), mais peut etre distinct (ex. rediriger vers un
    # autre email que le compte SMTP utilise pour l'envoi).
    notify_email: str | None = None

    # --- Sources externes ---
    benzinga_api_key: str | None = None
    log_level: str = "INFO"

    # --- Portefeuille virtuel de simulation (Etape 12) ---
    # Cash de depart du portefeuille simule - purement pedagogique, aucun
    # lien avec de l'argent reel (voir docs/17-limites-legales-techniques.md).
    portfolio_starting_cash: float = 10000.0
    # Frais et slippage (Etape 17) : sans eux, une simulation surestime la
    # performance de 5 a 15% (voir docs/11 et le guide de backtesting cite en
    # discussion). Commission fixe par ordre + slippage defavorable en %
    # applique au cours execute (achat plus cher, vente moins bien payee).
    portfolio_commission_per_trade: float = 2.0
    portfolio_slippage_pct: float = 0.001


@lru_cache
def get_settings() -> Settings:
    """Point d'acces unique aux settings (mis en cache, lu une seule fois)."""
    return Settings()
