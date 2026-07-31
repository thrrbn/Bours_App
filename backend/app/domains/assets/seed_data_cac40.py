"""
Donnees de seed pour l'indice CAC 40 (Euronext Paris). Composition verifiee
via zonebourse.com le 30/07/2026 (39 valeurs recuperees sur les ~40 - liste
non garantie exhaustive a la ligne pres, a corriger soi-meme si la
composition change - meme principe que seed_data.py pour le BEL20).

ArcelorMittal, membre a la fois du CAC 40 et de l'AEX, est seede une seule
fois sous market="EURONEXT_AMSTERDAM" (voir seed_data_aex.py) pour eviter un
doublon de ticker/ingestion - c'est un choix arbitraire, pas une regle
Euronext.

Tickers au format Yahoo Finance (suffixe .PA = Euronext Paris).
"""

CAC40_ASSETS: list[dict] = [
    {"ticker": "MC.PA", "name": "LVMH", "market": "EURONEXT_PARIS", "sector": "Luxe", "currency": "EUR", "isin": None},
    {"ticker": "OR.PA", "name": "L'Oreal", "market": "EURONEXT_PARIS", "sector": "Cosmetiques", "currency": "EUR", "isin": None},
    {"ticker": "RMS.PA", "name": "Hermes International", "market": "EURONEXT_PARIS", "sector": "Luxe", "currency": "EUR", "isin": None},
    {"ticker": "AIR.PA", "name": "Airbus", "market": "EURONEXT_PARIS", "sector": "Aeronautique", "currency": "EUR", "isin": None},
    {"ticker": "SU.PA", "name": "Schneider Electric", "market": "EURONEXT_PARIS", "sector": "Equipement electrique", "currency": "EUR", "isin": None},
    {"ticker": "TTE.PA", "name": "TotalEnergies", "market": "EURONEXT_PARIS", "sector": "Energie", "currency": "EUR", "isin": None},
    {"ticker": "SAF.PA", "name": "Safran", "market": "EURONEXT_PARIS", "sector": "Aeronautique", "currency": "EUR", "isin": None},
    {"ticker": "AI.PA", "name": "Air Liquide", "market": "EURONEXT_PARIS", "sector": "Chimie", "currency": "EUR", "isin": None},
    {"ticker": "BNP.PA", "name": "BNP Paribas", "market": "EURONEXT_PARIS", "sector": "Banque", "currency": "EUR", "isin": None},
    {"ticker": "SAN.PA", "name": "Sanofi", "market": "EURONEXT_PARIS", "sector": "Pharmaceutique", "currency": "EUR", "isin": None},
    {"ticker": "CS.PA", "name": "AXA", "market": "EURONEXT_PARIS", "sector": "Assurance", "currency": "EUR", "isin": None},
    {"ticker": "EL.PA", "name": "EssilorLuxottica", "market": "EURONEXT_PARIS", "sector": "Optique", "currency": "EUR", "isin": None},
    {"ticker": "DG.PA", "name": "Vinci", "market": "EURONEXT_PARIS", "sector": "Construction / BTP", "currency": "EUR", "isin": None},
    {"ticker": "ENGI.PA", "name": "Engie", "market": "EURONEXT_PARIS", "sector": "Energie / utilities", "currency": "EUR", "isin": None},
    {"ticker": "GLE.PA", "name": "Societe Generale", "market": "EURONEXT_PARIS", "sector": "Banque", "currency": "EUR", "isin": None},
    {"ticker": "STMPA.PA", "name": "STMicroelectronics", "market": "EURONEXT_PARIS", "sector": "Semi-conducteurs", "currency": "EUR", "isin": None},
    {"ticker": "ACA.PA", "name": "Credit Agricole", "market": "EURONEXT_PARIS", "sector": "Banque", "currency": "EUR", "isin": None},
    {"ticker": "HO.PA", "name": "Thales", "market": "EURONEXT_PARIS", "sector": "Defense / electronique", "currency": "EUR", "isin": None},
    {"ticker": "BN.PA", "name": "Danone", "market": "EURONEXT_PARIS", "sector": "Agroalimentaire", "currency": "EUR", "isin": None},
    {"ticker": "ORA.PA", "name": "Orange", "market": "EURONEXT_PARIS", "sector": "Telecom", "currency": "EUR", "isin": None},
    {"ticker": "SGO.PA", "name": "Saint-Gobain", "market": "EURONEXT_PARIS", "sector": "Materiaux de construction", "currency": "EUR", "isin": None},
    {"ticker": "LR.PA", "name": "Legrand", "market": "EURONEXT_PARIS", "sector": "Equipement electrique", "currency": "EUR", "isin": None},
    {"ticker": "KER.PA", "name": "Kering", "market": "EURONEXT_PARIS", "sector": "Luxe", "currency": "EUR", "isin": None},
    {"ticker": "VIE.PA", "name": "Veolia Environnement", "market": "EURONEXT_PARIS", "sector": "Environnement / utilities", "currency": "EUR", "isin": None},
    {"ticker": "DSY.PA", "name": "Dassault Systemes", "market": "EURONEXT_PARIS", "sector": "Logiciels", "currency": "EUR", "isin": None},
    {"ticker": "ML.PA", "name": "Michelin", "market": "EURONEXT_PARIS", "sector": "Pneumatiques", "currency": "EUR", "isin": None},
    {"ticker": "PUB.PA", "name": "Publicis Groupe", "market": "EURONEXT_PARIS", "sector": "Communication / publicite", "currency": "EUR", "isin": None},
    {"ticker": "EN.PA", "name": "Bouygues", "market": "EURONEXT_PARIS", "sector": "Construction / telecom", "currency": "EUR", "isin": None},
    {"ticker": "RI.PA", "name": "Pernod Ricard", "market": "EURONEXT_PARIS", "sector": "Boissons", "currency": "EUR", "isin": None},
    {"ticker": "CAP.PA", "name": "Capgemini", "market": "EURONEXT_PARIS", "sector": "Services informatiques", "currency": "EUR", "isin": None},
    {"ticker": "STLAP.PA", "name": "Stellantis", "market": "EURONEXT_PARIS", "sector": "Automobile", "currency": "EUR", "isin": None},
    {"ticker": "ENX.PA", "name": "Euronext", "market": "EURONEXT_PARIS", "sector": "Infrastructure de marche", "currency": "EUR", "isin": None},
    {"ticker": "URW.PA", "name": "Unibail-Rodamco-Westfield", "market": "EURONEXT_PARIS", "sector": "Immobilier commercial (REIT)", "currency": "EUR", "isin": None},
    {"ticker": "FGR.PA", "name": "Eiffage", "market": "EURONEXT_PARIS", "sector": "Construction / BTP", "currency": "EUR", "isin": None},
    {"ticker": "ERF.PA", "name": "Eurofins Scientific", "market": "EURONEXT_PARIS", "sector": "Analyses / laboratoires", "currency": "EUR", "isin": None},
    {"ticker": "BVI.PA", "name": "Bureau Veritas", "market": "EURONEXT_PARIS", "sector": "Certification / inspection", "currency": "EUR", "isin": None},
    {"ticker": "CA.PA", "name": "Carrefour", "market": "EURONEXT_PARIS", "sector": "Distribution", "currency": "EUR", "isin": None},
    {"ticker": "AC.PA", "name": "Accor", "market": "EURONEXT_PARIS", "sector": "Hotellerie", "currency": "EUR", "isin": None},
    {"ticker": "RNO.PA", "name": "Renault", "market": "EURONEXT_PARIS", "sector": "Automobile", "currency": "EUR", "isin": None},
]
