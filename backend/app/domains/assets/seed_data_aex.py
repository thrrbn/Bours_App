"""
Donnees de seed pour l'indice AEX (Euronext Amsterdam). Composition
verifiee via Wikipedia (source primaire : live.euronext.com), a jour au
31/12/2024 - a corriger soi-meme si la composition change depuis (revues
quatre fois par an), meme principe que seed_data.py pour le BEL20.

Tickers au format Yahoo Finance (suffixe .AS = Euronext Amsterdam).
"""

AEX_ASSETS: list[dict] = [
    {"ticker": "ABN.AS", "name": "ABN AMRO", "market": "EURONEXT_AMSTERDAM", "sector": "Banque", "currency": "EUR", "isin": None},
    {"ticker": "ADYEN.AS", "name": "Adyen", "market": "EURONEXT_AMSTERDAM", "sector": "Paiements / fintech", "currency": "EUR", "isin": None},
    {"ticker": "AGN.AS", "name": "Aegon", "market": "EURONEXT_AMSTERDAM", "sector": "Assurance", "currency": "EUR", "isin": None},
    {"ticker": "AD.AS", "name": "Ahold Delhaize", "market": "EURONEXT_AMSTERDAM", "sector": "Distribution", "currency": "EUR", "isin": None},
    {"ticker": "AKZA.AS", "name": "AkzoNobel", "market": "EURONEXT_AMSTERDAM", "sector": "Chimie / peintures", "currency": "EUR", "isin": None},
    {"ticker": "MT.AS", "name": "ArcelorMittal", "market": "EURONEXT_AMSTERDAM", "sector": "Aciers", "currency": "EUR", "isin": None},
    {"ticker": "ASM.AS", "name": "ASM International", "market": "EURONEXT_AMSTERDAM", "sector": "Equipement semi-conducteurs", "currency": "EUR", "isin": None},
    {"ticker": "ASML.AS", "name": "ASML Holding", "market": "EURONEXT_AMSTERDAM", "sector": "Equipement semi-conducteurs", "currency": "EUR", "isin": None},
    {"ticker": "ASRNL.AS", "name": "ASR Nederland", "market": "EURONEXT_AMSTERDAM", "sector": "Assurance", "currency": "EUR", "isin": None},
    {"ticker": "BESI.AS", "name": "BE Semiconductor Industries", "market": "EURONEXT_AMSTERDAM", "sector": "Equipement semi-conducteurs", "currency": "EUR", "isin": None},
    {"ticker": "DSFIR.AS", "name": "DSM-Firmenich", "market": "EURONEXT_AMSTERDAM", "sector": "Chimie / nutrition", "currency": "EUR", "isin": None},
    {"ticker": "EXO.AS", "name": "Exor", "market": "EURONEXT_AMSTERDAM", "sector": "Holding financier", "currency": "EUR", "isin": None},
    {"ticker": "HEIA.AS", "name": "Heineken", "market": "EURONEXT_AMSTERDAM", "sector": "Boissons", "currency": "EUR", "isin": None},
    {"ticker": "IMCD.AS", "name": "IMCD", "market": "EURONEXT_AMSTERDAM", "sector": "Distribution chimique", "currency": "EUR", "isin": None},
    {"ticker": "INGA.AS", "name": "ING Group", "market": "EURONEXT_AMSTERDAM", "sector": "Banque", "currency": "EUR", "isin": None},
    {"ticker": "KPN.AS", "name": "KPN", "market": "EURONEXT_AMSTERDAM", "sector": "Telecom", "currency": "EUR", "isin": None},
    {"ticker": "NN.AS", "name": "NN Group", "market": "EURONEXT_AMSTERDAM", "sector": "Assurance", "currency": "EUR", "isin": None},
    {"ticker": "PHIA.AS", "name": "Philips", "market": "EURONEXT_AMSTERDAM", "sector": "Equipement medical", "currency": "EUR", "isin": None},
    {"ticker": "PRX.AS", "name": "Prosus", "market": "EURONEXT_AMSTERDAM", "sector": "Technologie / investissement", "currency": "EUR", "isin": None},
    {"ticker": "RAND.AS", "name": "Randstad", "market": "EURONEXT_AMSTERDAM", "sector": "Services RH / interim", "currency": "EUR", "isin": None},
    {"ticker": "REN.AS", "name": "RELX", "market": "EURONEXT_AMSTERDAM", "sector": "Edition / information professionnelle", "currency": "EUR", "isin": None},
    {"ticker": "SHELL.AS", "name": "Shell", "market": "EURONEXT_AMSTERDAM", "sector": "Energie", "currency": "EUR", "isin": None},
    {"ticker": "UMG.AS", "name": "Universal Music Group", "market": "EURONEXT_AMSTERDAM", "sector": "Media / musique", "currency": "EUR", "isin": None},
    {"ticker": "UNA.AS", "name": "Unilever", "market": "EURONEXT_AMSTERDAM", "sector": "Biens de consommation", "currency": "EUR", "isin": None},
    {"ticker": "WKL.AS", "name": "Wolters Kluwer", "market": "EURONEXT_AMSTERDAM", "sector": "Edition / information professionnelle", "currency": "EUR", "isin": None},
]
