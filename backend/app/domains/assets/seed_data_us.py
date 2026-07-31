"""
Donnees de seed pour un panier de grandes capitalisations americaines
(indice de reference informel, pas un indice officiel unique - S&P 500 pour
la plupart, quelques valeurs Dow Jones). Meme logique que les autres fichiers
seed_data_*.py : liste statique, idempotente, a completer via
POST /api/v1/assets si besoin d'un ticker absent d'ici.

Tickers au format Yahoo Finance US (sans suffixe de place boursiere).
Marche indique = bourse de cotation reelle (NASDAQ ou NYSE), a titre
informatif uniquement - le provider (Yahoo Finance) est le meme pour les
deux, seul market_data.service.provider_for_market() distingue "BINANCE" du
reste.
"""

US_MAJORS_ASSETS: list[dict] = [
    {"ticker": "AAPL", "name": "Apple", "market": "NASDAQ", "sector": "Technologie", "currency": "USD", "isin": None},
    {"ticker": "MSFT", "name": "Microsoft", "market": "NASDAQ", "sector": "Technologie", "currency": "USD", "isin": None},
    {"ticker": "NVDA", "name": "Nvidia", "market": "NASDAQ", "sector": "Semi-conducteurs", "currency": "USD", "isin": None},
    {"ticker": "AMZN", "name": "Amazon", "market": "NASDAQ", "sector": "Distribution / e-commerce", "currency": "USD", "isin": None},
    {"ticker": "GOOGL", "name": "Alphabet (Google)", "market": "NASDAQ", "sector": "Technologie", "currency": "USD", "isin": None},
    {"ticker": "META", "name": "Meta Platforms", "market": "NASDAQ", "sector": "Technologie", "currency": "USD", "isin": None},
    {"ticker": "TSLA", "name": "Tesla", "market": "NASDAQ", "sector": "Automobile", "currency": "USD", "isin": None},
    {"ticker": "BRK-B", "name": "Berkshire Hathaway", "market": "NYSE", "sector": "Holding financier", "currency": "USD", "isin": None},
    {"ticker": "JPM", "name": "JPMorgan Chase", "market": "NYSE", "sector": "Banque", "currency": "USD", "isin": None},
    {"ticker": "V", "name": "Visa", "market": "NYSE", "sector": "Services financiers", "currency": "USD", "isin": None},
    {"ticker": "MA", "name": "Mastercard", "market": "NYSE", "sector": "Services financiers", "currency": "USD", "isin": None},
    {"ticker": "JNJ", "name": "Johnson & Johnson", "market": "NYSE", "sector": "Pharmaceutique", "currency": "USD", "isin": None},
    {"ticker": "WMT", "name": "Walmart", "market": "NYSE", "sector": "Distribution", "currency": "USD", "isin": None},
    {"ticker": "XOM", "name": "ExxonMobil", "market": "NYSE", "sector": "Energie", "currency": "USD", "isin": None},
    {"ticker": "UNH", "name": "UnitedHealth Group", "market": "NYSE", "sector": "Assurance sante", "currency": "USD", "isin": None},
    {"ticker": "PG", "name": "Procter & Gamble", "market": "NYSE", "sector": "Biens de consommation", "currency": "USD", "isin": None},
    {"ticker": "HD", "name": "Home Depot", "market": "NYSE", "sector": "Distribution", "currency": "USD", "isin": None},
    {"ticker": "CVX", "name": "Chevron", "market": "NYSE", "sector": "Energie", "currency": "USD", "isin": None},
    {"ticker": "AVGO", "name": "Broadcom", "market": "NASDAQ", "sector": "Semi-conducteurs", "currency": "USD", "isin": None},
    {"ticker": "LLY", "name": "Eli Lilly", "market": "NYSE", "sector": "Pharmaceutique", "currency": "USD", "isin": None},
    {"ticker": "KO", "name": "Coca-Cola", "market": "NYSE", "sector": "Boissons", "currency": "USD", "isin": None},
    {"ticker": "PEP", "name": "PepsiCo", "market": "NASDAQ", "sector": "Boissons", "currency": "USD", "isin": None},
    {"ticker": "COST", "name": "Costco", "market": "NASDAQ", "sector": "Distribution", "currency": "USD", "isin": None},
    {"ticker": "ADBE", "name": "Adobe", "market": "NASDAQ", "sector": "Logiciels", "currency": "USD", "isin": None},
    {"ticker": "NFLX", "name": "Netflix", "market": "NASDAQ", "sector": "Media / streaming", "currency": "USD", "isin": None},
    {"ticker": "AMD", "name": "Advanced Micro Devices", "market": "NASDAQ", "sector": "Semi-conducteurs", "currency": "USD", "isin": None},
    {"ticker": "CRM", "name": "Salesforce", "market": "NYSE", "sector": "Logiciels", "currency": "USD", "isin": None},
    {"ticker": "INTC", "name": "Intel", "market": "NASDAQ", "sector": "Semi-conducteurs", "currency": "USD", "isin": None},
    {"ticker": "DIS", "name": "Walt Disney", "market": "NYSE", "sector": "Media", "currency": "USD", "isin": None},
    {"ticker": "BA", "name": "Boeing", "market": "NYSE", "sector": "Aeronautique", "currency": "USD", "isin": None},
    {"ticker": "PFE", "name": "Pfizer", "market": "NYSE", "sector": "Pharmaceutique", "currency": "USD", "isin": None},
    {"ticker": "ORCL", "name": "Oracle", "market": "NYSE", "sector": "Logiciels", "currency": "USD", "isin": None},
    {"ticker": "IBM", "name": "IBM", "market": "NYSE", "sector": "Technologie", "currency": "USD", "isin": None},
    {"ticker": "NKE", "name": "Nike", "market": "NYSE", "sector": "Habillement", "currency": "USD", "isin": None},
]
