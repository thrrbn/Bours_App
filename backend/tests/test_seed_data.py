"""
Garde-fous sur les fichiers assets/seed_data*.py : chaque liste statique doit
rester interne coherente (pas de ticker duplique dans un meme market, sinon
`repository.bulk_upsert` silencieusement n'inserer que la premiere
occurrence via ON CONFLICT DO NOTHING) et chaque ligne doit avoir les champs
requis par AssetCreate. Tests purs, aucune base de donnees necessaire.
"""
from app.domains.assets.seed_data import BEL20_ASSETS
from app.domains.assets.seed_data_aex import AEX_ASSETS
from app.domains.assets.seed_data_binance import BINANCE_MAJORS_ASSETS
from app.domains.assets.seed_data_cac40 import CAC40_ASSETS
from app.domains.assets.seed_data_dax import DAX40_ASSETS
from app.domains.assets.seed_data_us import US_MAJORS_ASSETS

ALL_SEED_LISTS = {
    "BEL20": BEL20_ASSETS,
    "CAC40": CAC40_ASSETS,
    "DAX40": DAX40_ASSETS,
    "AEX": AEX_ASSETS,
    "US_MAJORS": US_MAJORS_ASSETS,
    "BINANCE_MAJORS": BINANCE_MAJORS_ASSETS,
}

REQUIRED_FIELDS = {"ticker", "name", "market", "sector", "currency", "isin"}


def test_each_seed_list_is_non_empty():
    for name, rows in ALL_SEED_LISTS.items():
        assert len(rows) > 0, f"{name} est vide"


def test_each_seed_list_has_no_duplicate_ticker():
    """Meme marche => meme provider => un doublon de ticker ecraserait
    silencieusement une ligne via ON CONFLICT DO NOTHING (bulk_upsert)."""
    for name, rows in ALL_SEED_LISTS.items():
        tickers = [row["ticker"] for row in rows]
        duplicates = {t for t in tickers if tickers.count(t) > 1}
        assert not duplicates, f"{name} contient des tickers dupliques: {duplicates}"


def test_each_seed_row_has_required_fields():
    for name, rows in ALL_SEED_LISTS.items():
        for row in rows:
            assert REQUIRED_FIELDS <= row.keys(), f"{name}: champ manquant dans {row}"
            assert row["ticker"], f"{name}: ticker vide dans {row}"
            assert row["market"], f"{name}: market vide dans {row}"


def test_no_ticker_market_collision_across_seed_lists():
    """Deux listes differentes pourraient accidentellement se recouvrir
    (ex. une valeur ajoutee deux fois par erreur sous le meme market)."""
    seen: dict[tuple[str, str], str] = {}
    for name, rows in ALL_SEED_LISTS.items():
        for row in rows:
            key = (row["ticker"], row["market"])
            assert key not in seen, f"{key} present a la fois dans {seen.get(key)} et {name}"
            seen[key] = name


def test_binance_assets_all_use_binance_market_for_provider_routing():
    """Necessaire pour que market_data.service.provider_for_market() route
    bien ces actifs vers BinanceProvider plutot que Yahoo Finance."""
    for row in BINANCE_MAJORS_ASSETS:
        assert row["market"] == "BINANCE"
