"""
Donnees de seed pour l'indice DAX 40 (Xetra / Bourse de Francfort).
Composition verifiee via Wikipedia (dax-indices.com comme source primaire
citee), a jour au 22/09/2025 - a corriger soi-meme si la composition change
depuis (revue trimestrielle), meme principe que seed_data.py pour le BEL20.

Airbus, membre a la fois du DAX et du CAC 40, est seede une seule fois sous
market="EURONEXT_PARIS" (voir seed_data_cac40.py) pour eviter un doublon de
ticker/ingestion.

Tickers au format Yahoo Finance (suffixe .DE = Xetra / Francfort).
"""

DAX40_ASSETS: list[dict] = [
    {"ticker": "ADS.DE", "name": "Adidas", "market": "XETRA", "sector": "Habillement", "currency": "EUR", "isin": None},
    {"ticker": "ALV.DE", "name": "Allianz", "market": "XETRA", "sector": "Assurance", "currency": "EUR", "isin": None},
    {"ticker": "BAS.DE", "name": "BASF", "market": "XETRA", "sector": "Chimie", "currency": "EUR", "isin": None},
    {"ticker": "BAYN.DE", "name": "Bayer", "market": "XETRA", "sector": "Pharmaceutique", "currency": "EUR", "isin": None},
    {"ticker": "BEI.DE", "name": "Beiersdorf", "market": "XETRA", "sector": "Biens de consommation", "currency": "EUR", "isin": None},
    {"ticker": "BMW.DE", "name": "BMW", "market": "XETRA", "sector": "Automobile", "currency": "EUR", "isin": None},
    {"ticker": "BNR.DE", "name": "Brenntag", "market": "XETRA", "sector": "Distribution chimique", "currency": "EUR", "isin": None},
    {"ticker": "CBK.DE", "name": "Commerzbank", "market": "XETRA", "sector": "Banque", "currency": "EUR", "isin": None},
    {"ticker": "CON.DE", "name": "Continental", "market": "XETRA", "sector": "Automobile", "currency": "EUR", "isin": None},
    {"ticker": "DTG.DE", "name": "Daimler Truck", "market": "XETRA", "sector": "Automobile", "currency": "EUR", "isin": None},
    {"ticker": "DBK.DE", "name": "Deutsche Bank", "market": "XETRA", "sector": "Banque", "currency": "EUR", "isin": None},
    {"ticker": "DB1.DE", "name": "Deutsche Boerse", "market": "XETRA", "sector": "Infrastructure de marche", "currency": "EUR", "isin": None},
    {"ticker": "DHL.DE", "name": "Deutsche Post (DHL)", "market": "XETRA", "sector": "Logistique", "currency": "EUR", "isin": None},
    {"ticker": "DTE.DE", "name": "Deutsche Telekom", "market": "XETRA", "sector": "Telecom", "currency": "EUR", "isin": None},
    {"ticker": "EOAN.DE", "name": "E.ON", "market": "XETRA", "sector": "Energie / utilities", "currency": "EUR", "isin": None},
    {"ticker": "FRE.DE", "name": "Fresenius", "market": "XETRA", "sector": "Sante", "currency": "EUR", "isin": None},
    {"ticker": "FME.DE", "name": "Fresenius Medical Care", "market": "XETRA", "sector": "Sante", "currency": "EUR", "isin": None},
    {"ticker": "G1A.DE", "name": "GEA Group", "market": "XETRA", "sector": "Ingenierie mecanique", "currency": "EUR", "isin": None},
    {"ticker": "HNR1.DE", "name": "Hannover Re", "market": "XETRA", "sector": "Reassurance", "currency": "EUR", "isin": None},
    {"ticker": "HEI.DE", "name": "Heidelberg Materials", "market": "XETRA", "sector": "Materiaux de construction", "currency": "EUR", "isin": None},
    {"ticker": "HEN3.DE", "name": "Henkel", "market": "XETRA", "sector": "Biens de consommation", "currency": "EUR", "isin": None},
    {"ticker": "IFX.DE", "name": "Infineon Technologies", "market": "XETRA", "sector": "Semi-conducteurs", "currency": "EUR", "isin": None},
    {"ticker": "MBG.DE", "name": "Mercedes-Benz Group", "market": "XETRA", "sector": "Automobile", "currency": "EUR", "isin": None},
    {"ticker": "MRK.DE", "name": "Merck (Allemagne)", "market": "XETRA", "sector": "Pharmaceutique", "currency": "EUR", "isin": None},
    {"ticker": "MTX.DE", "name": "MTU Aero Engines", "market": "XETRA", "sector": "Aeronautique", "currency": "EUR", "isin": None},
    {"ticker": "MUV2.DE", "name": "Munich Re", "market": "XETRA", "sector": "Reassurance", "currency": "EUR", "isin": None},
    {"ticker": "PAH3.DE", "name": "Porsche SE", "market": "XETRA", "sector": "Automobile (holding)", "currency": "EUR", "isin": None},
    {"ticker": "QIA.DE", "name": "Qiagen", "market": "XETRA", "sector": "Biotechnologie", "currency": "EUR", "isin": None},
    {"ticker": "RHM.DE", "name": "Rheinmetall", "market": "XETRA", "sector": "Defense", "currency": "EUR", "isin": None},
    {"ticker": "RWE.DE", "name": "RWE", "market": "XETRA", "sector": "Energie / utilities", "currency": "EUR", "isin": None},
    {"ticker": "SAP.DE", "name": "SAP", "market": "XETRA", "sector": "Logiciels", "currency": "EUR", "isin": None},
    {"ticker": "G24.DE", "name": "Scout24", "market": "XETRA", "sector": "E-commerce", "currency": "EUR", "isin": None},
    {"ticker": "SIE.DE", "name": "Siemens", "market": "XETRA", "sector": "Industrie", "currency": "EUR", "isin": None},
    {"ticker": "ENR.DE", "name": "Siemens Energy", "market": "XETRA", "sector": "Energie", "currency": "EUR", "isin": None},
    {"ticker": "SHL.DE", "name": "Siemens Healthineers", "market": "XETRA", "sector": "Equipement medical", "currency": "EUR", "isin": None},
    {"ticker": "SY1.DE", "name": "Symrise", "market": "XETRA", "sector": "Chimie / aromes", "currency": "EUR", "isin": None},
    {"ticker": "VOW3.DE", "name": "Volkswagen Group", "market": "XETRA", "sector": "Automobile", "currency": "EUR", "isin": None},
    {"ticker": "VNA.DE", "name": "Vonovia", "market": "XETRA", "sector": "Immobilier residentiel", "currency": "EUR", "isin": None},
    {"ticker": "ZAL.DE", "name": "Zalando", "market": "XETRA", "sector": "E-commerce", "currency": "EUR", "isin": None},
]
