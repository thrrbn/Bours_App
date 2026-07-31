"""
Donnees de seed pour un panier de cryptomonnaies cotees sur Binance (paires
USDT au comptant). Meme logique que seed_data.py (BEL20) : liste statique,
idempotente (voir repository.bulk_upsert), a completer soi-meme via
POST /api/v1/assets si besoin d'une paire absente d'ici - toute paire valide
sur https://api.binance.com/api/v3/klines fonctionne des lors qu'un Asset
avec market="BINANCE" et ce ticker existe (le frontend et l'ingestion ne
distinguent pas les actifs seedes ici des actifs ajoutes manuellement).

Volontairement PAS "toutes les paires Binance" (il en existe plus de 2000,
beaucoup illiquides/speculatives) : ~32 grandes capitalisations reconnues,
pour deux raisons pratiques -
  1. l'ingestion des prix reste sequentielle (voir jobs/ingest_prices_job.py,
     meme contrainte de debit que Yahoo Finance meme si Binance n'a pas de
     429 documente comme Yahoo) - un panier demesure allonge /refresh-all
     pour peu de valeur ajoutee analytique ;
  2. coherent avec l'esprit "actifs suivis deliberement, jamais un ecran
     de cotation generaliste" du reste du projet (BEL20 = 20 valeurs, pas
     "toute la bourse de Bruxelles").
Tickers au format Binance (symbol, sans separateur) : voir
market_data/providers/binance.py.
"""

BINANCE_MAJORS_ASSETS: list[dict] = [
    {"ticker": "BTCUSDT", "name": "Bitcoin", "market": "BINANCE", "sector": "Cryptomonnaie", "currency": "USDT", "isin": None},
    {"ticker": "ETHUSDT", "name": "Ethereum", "market": "BINANCE", "sector": "Cryptomonnaie", "currency": "USDT", "isin": None},
    {"ticker": "BNBUSDT", "name": "BNB", "market": "BINANCE", "sector": "Cryptomonnaie", "currency": "USDT", "isin": None},
    {"ticker": "SOLUSDT", "name": "Solana", "market": "BINANCE", "sector": "Cryptomonnaie", "currency": "USDT", "isin": None},
    {"ticker": "XRPUSDT", "name": "XRP", "market": "BINANCE", "sector": "Cryptomonnaie", "currency": "USDT", "isin": None},
    {"ticker": "ADAUSDT", "name": "Cardano", "market": "BINANCE", "sector": "Cryptomonnaie", "currency": "USDT", "isin": None},
    {"ticker": "DOGEUSDT", "name": "Dogecoin", "market": "BINANCE", "sector": "Cryptomonnaie", "currency": "USDT", "isin": None},
    {"ticker": "AVAXUSDT", "name": "Avalanche", "market": "BINANCE", "sector": "Cryptomonnaie", "currency": "USDT", "isin": None},
    {"ticker": "TRXUSDT", "name": "TRON", "market": "BINANCE", "sector": "Cryptomonnaie", "currency": "USDT", "isin": None},
    {"ticker": "DOTUSDT", "name": "Polkadot", "market": "BINANCE", "sector": "Cryptomonnaie", "currency": "USDT", "isin": None},
    {"ticker": "LINKUSDT", "name": "Chainlink", "market": "BINANCE", "sector": "Cryptomonnaie", "currency": "USDT", "isin": None},
    {"ticker": "POLUSDT", "name": "Polygon (POL)", "market": "BINANCE", "sector": "Cryptomonnaie", "currency": "USDT", "isin": None},  # ex-MATIC, ticker Binance renomme sept. 2024
    {"ticker": "LTCUSDT", "name": "Litecoin", "market": "BINANCE", "sector": "Cryptomonnaie", "currency": "USDT", "isin": None},
    {"ticker": "BCHUSDT", "name": "Bitcoin Cash", "market": "BINANCE", "sector": "Cryptomonnaie", "currency": "USDT", "isin": None},
    {"ticker": "ICPUSDT", "name": "Internet Computer", "market": "BINANCE", "sector": "Cryptomonnaie", "currency": "USDT", "isin": None},
    {"ticker": "UNIUSDT", "name": "Uniswap", "market": "BINANCE", "sector": "Cryptomonnaie", "currency": "USDT", "isin": None},
    {"ticker": "ETCUSDT", "name": "Ethereum Classic", "market": "BINANCE", "sector": "Cryptomonnaie", "currency": "USDT", "isin": None},
    {"ticker": "ATOMUSDT", "name": "Cosmos", "market": "BINANCE", "sector": "Cryptomonnaie", "currency": "USDT", "isin": None},
    {"ticker": "XLMUSDT", "name": "Stellar", "market": "BINANCE", "sector": "Cryptomonnaie", "currency": "USDT", "isin": None},
    {"ticker": "HBARUSDT", "name": "Hedera", "market": "BINANCE", "sector": "Cryptomonnaie", "currency": "USDT", "isin": None},
    {"ticker": "VETUSDT", "name": "VeChain", "market": "BINANCE", "sector": "Cryptomonnaie", "currency": "USDT", "isin": None},
    {"ticker": "ALGOUSDT", "name": "Algorand", "market": "BINANCE", "sector": "Cryptomonnaie", "currency": "USDT", "isin": None},
    {"ticker": "ARBUSDT", "name": "Arbitrum", "market": "BINANCE", "sector": "Cryptomonnaie", "currency": "USDT", "isin": None},
    {"ticker": "OPUSDT", "name": "Optimism", "market": "BINANCE", "sector": "Cryptomonnaie", "currency": "USDT", "isin": None},
    {"ticker": "INJUSDT", "name": "Injective", "market": "BINANCE", "sector": "Cryptomonnaie", "currency": "USDT", "isin": None},
    {"ticker": "SUIUSDT", "name": "Sui", "market": "BINANCE", "sector": "Cryptomonnaie", "currency": "USDT", "isin": None},
    {"ticker": "FILUSDT", "name": "Filecoin", "market": "BINANCE", "sector": "Cryptomonnaie", "currency": "USDT", "isin": None},
    {"ticker": "AAVEUSDT", "name": "Aave", "market": "BINANCE", "sector": "Cryptomonnaie", "currency": "USDT", "isin": None},
    {"ticker": "MKRUSDT", "name": "Maker", "market": "BINANCE", "sector": "Cryptomonnaie", "currency": "USDT", "isin": None},
    {"ticker": "NEARUSDT", "name": "NEAR Protocol", "market": "BINANCE", "sector": "Cryptomonnaie", "currency": "USDT", "isin": None},
    {"ticker": "SHIBUSDT", "name": "Shiba Inu", "market": "BINANCE", "sector": "Cryptomonnaie", "currency": "USDT", "isin": None},
    {"ticker": "TONUSDT", "name": "Toncoin", "market": "BINANCE", "sector": "Cryptomonnaie", "currency": "USDT", "isin": None},
]
