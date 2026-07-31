"""
Traduction FR des extraits d'articles (31/07/2026) - la plupart des sources
US (Yahoo Finance US, Google News en anglais) fournissent des titres/extraits
en anglais. Utilise `deep-translator` (backend GoogleTranslator, appel HTTP
non officiel vers translate.google.com - PAS d'API contractuelle ni de cle,
meme categorie de fragilite que yfinance/les flux RSS deja documentee dans
docs/17-limites-legales-techniques.md).

NON TESTE en conditions reelles lors de l'ecriture : le sandbox de
developpement utilise pour ce projet n'a pas d'acces reseau sortant vers
translate.google.com (bloque par le proxy sortant, meme limite que torch/
download.pytorch.org - voir Dockerfile). A verifier au premier appel reel
apres rebuild (voir news/service.py::summarize_article, qui appelle cette
fonction) - si l'appel echoue systematiquement en production, le texte
original (non traduit) est renvoye tel quel (voir le try/except ci-dessous),
donc la fonctionnalite se degrade sans jamais casser le reste du resume.
"""
import logging

logger = logging.getLogger(__name__)


def translate_to_french(text: str) -> str:
    """
    Traduit `text` vers le francais (detection automatique de la langue
    source - un texte deja en francais ressort generalement inchange).
    Retourne le texte ORIGINAL si la traduction echoue (reseau, endpoint
    indisponible, texte vide...) plutot que de lever une exception - la
    traduction est un enrichissement, jamais un pre-requis pour afficher un
    resume (voir summarize_article).
    """
    if not text or not text.strip():
        return text
    try:
        # Import local (pas en tete de module) : si `deep-translator` n'est
        # pas encore installe (avant un rebuild du conteneur backend), le
        # ImportError est capture par le except ci-dessous comme n'importe
        # quel autre echec - degrade en douceur plutot que de faire planter
        # tout le module news au demarrage de l'app.
        from deep_translator import GoogleTranslator

        translated = GoogleTranslator(source="auto", target="fr").translate(text)
        return translated or text
    except Exception:
        logger.warning("Echec de traduction FR (texte conserve tel quel)", exc_info=True)
        return text
