"""
Donnees de seed pour les 20 composants de l'indice BEL 20 (Euronext Bruxelles).

Miroir exact de db/migrations/004_bel20_seed.sql : ce fichier SQL n'est
applique automatiquement que si le conteneur Postgres demarre sur un volume
VIDE (docker-entrypoint-initdb.d) ; il ne joue donc aucun role si la base a
ete initialisee via `alembic upgrade head` (chemin canonique depuis le
25/07/2026, voir README.md). D'ou l'existence de cette version Python,
appelable a tout moment via POST /api/v1/maintenance/seed-bel20.

Composition verifiee via Euronext + EasyBourse en juillet 2026 - a corriger
soi-meme si la composition de l'indice change (revue annuelle en mars).
Tickers au format yfinance (suffixe .BR = cotation Euronext Bruxelles).
"""

BEL20_ASSETS: list[dict] = [
    {"ticker": "ACKB.BR", "name": "Ackermans & van Haaren", "market": "EURONEXT_BRUSSELS", "sector": "Holding financier", "currency": "EUR", "isin": "BE0003764785"},
    {"ticker": "AED.BR", "name": "Aedifica", "market": "EURONEXT_BRUSSELS", "sector": "Immobilier sante (REIT)", "currency": "EUR", "isin": "BE0003851681"},
    {"ticker": "AGS.BR", "name": "Ageas", "market": "EURONEXT_BRUSSELS", "sector": "Assurance", "currency": "EUR", "isin": "BE0974264930"},
    {"ticker": "ABI.BR", "name": "AB InBev", "market": "EURONEXT_BRUSSELS", "sector": "Boissons", "currency": "EUR", "isin": "BE0974293251"},
    {"ticker": "APAM.BR", "name": "Aperam", "market": "EURONEXT_BRUSSELS", "sector": "Aciers speciaux", "currency": "EUR", "isin": "LU0569974404"},
    {"ticker": "ARGX.BR", "name": "argenx", "market": "EURONEXT_BRUSSELS", "sector": "Biotechnologie", "currency": "EUR", "isin": "NL0010832176"},
    {"ticker": "AZE.BR", "name": "Azelis Group", "market": "EURONEXT_BRUSSELS", "sector": "Distribution chimique", "currency": "EUR", "isin": "BE0974400328"},
    {"ticker": "DIE.BR", "name": "D'Ieteren Group", "market": "EURONEXT_BRUSSELS", "sector": "Distribution automobile", "currency": "EUR", "isin": "BE0974259880"},
    {"ticker": "ELI.BR", "name": "Elia Group", "market": "EURONEXT_BRUSSELS", "sector": "Reseaux electriques", "currency": "EUR", "isin": "BE0003822393"},
    {"ticker": "GBLB.BR", "name": "GBL", "market": "EURONEXT_BRUSSELS", "sector": "Holding financier", "currency": "EUR", "isin": "BE0003797140"},
    {"ticker": "KBC.BR", "name": "KBC Group", "market": "EURONEXT_BRUSSELS", "sector": "Banque", "currency": "EUR", "isin": "BE0003565737"},
    {"ticker": "LOTB.BR", "name": "Lotus Bakeries", "market": "EURONEXT_BRUSSELS", "sector": "Agroalimentaire", "currency": "EUR", "isin": "BE0003604155"},
    {"ticker": "MELE.BR", "name": "Melexis", "market": "EURONEXT_BRUSSELS", "sector": "Semi-conducteurs", "currency": "EUR", "isin": "BE0165385973"},
    {"ticker": "MONT.BR", "name": "Montea", "market": "EURONEXT_BRUSSELS", "sector": "Immobilier logistique (REIT)", "currency": "EUR", "isin": "BE0003853703"},
    {"ticker": "SOF.BR", "name": "Sofina", "market": "EURONEXT_BRUSSELS", "sector": "Holding financier", "currency": "EUR", "isin": "BE0003717312"},
    {"ticker": "SOLB.BR", "name": "Solvay", "market": "EURONEXT_BRUSSELS", "sector": "Chimie", "currency": "EUR", "isin": "BE0003470755"},
    {"ticker": "SYENS.BR", "name": "Syensqo", "market": "EURONEXT_BRUSSELS", "sector": "Chimie de specialite", "currency": "EUR", "isin": "BE0974464977"},
    {"ticker": "UCB.BR", "name": "UCB", "market": "EURONEXT_BRUSSELS", "sector": "Pharmaceutique", "currency": "EUR", "isin": "BE0003739530"},
    {"ticker": "UMI.BR", "name": "Umicore", "market": "EURONEXT_BRUSSELS", "sector": "Chimie / materiaux", "currency": "EUR", "isin": "BE0974320526"},
    {"ticker": "WDP.BR", "name": "WDP", "market": "EURONEXT_BRUSSELS", "sector": "Immobilier logistique (REIT)", "currency": "EUR", "isin": "BE0974349814"},
]
