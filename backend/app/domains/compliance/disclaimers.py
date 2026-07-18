"""
Textes legaux centralises - source unique de verite, consommee a la fois par
l'API (endpoint /compliance/disclaimer) et par les templates d'explication
des signaux. Ne jamais dupliquer ce texte ailleurs dans le code.

Rappel : ceci n'est pas un texte juridique valide, a faire reviser par un
professionnel avant toute mise en production (voir docs/17).
"""

GENERAL_DISCLAIMER = (
    "Cette application fournit des scores statistiques et des scenarios probables a titre "
    "purement informatif. Elle ne constitue ni un conseil en investissement personnalise, ni "
    "une recommandation d'achat ou de vente, ni une garantie de performance future. Les "
    "performances passees ne prejugent pas des performances futures. Vous restez seul "
    "responsable de vos decisions d'investissement."
)

FORBIDDEN_TERMS = [
    "garanti",
    "garantie de gain",
    "conseil personnalise",
    "certain a 100%",
    "sans risque",
    "vous devez acheter",
    "vous devez vendre",
]
