# 9. Stratégie NLP / Sentiment — approche réaliste

## Principe : interprétabilité avant sophistication

Un modèle de deep learning entraîné sur mesure demanderait un volume de données annotées (article → impact réel sur le cours) que ni un particulier ni un solo développeur ne possède au démarrage. La stratégie retenue combine trois niveaux, du plus simple au plus complexe, **activables indépendamment** :

### Niveau 1 (MVP) — Lexique pondéré, fait main
Un dictionnaire `keyword → (poids, horizon_impact, polarité)` couvrant le vocabulaire financier demandé explicitement (achat, acquisition, restructuration, licenciement, guidance, profit warning, croissance, dette, fusion, dilution) et étendu à une trentaine d'autres termes financiers courants (rachat d'actions, dividende, litige, amende, rupture de contrat, record de résultat...).

```
"profit warning":    {poids: -0.8, horizon: "short",  polarité: négative}
"guidance relevée":  {poids: +0.6, horizon: "medium", polarité: positive}
"licenciement":      {poids: -0.4, horizon: "medium", polarité: négative}
"acquisition":       {poids: +0.3, horizon: "long",   polarité: incertaine}  # dépend du contexte
"dilution":          {poids: -0.5, horizon: "short",  polarité: négative}
```

**Score de sentiment d'un article** = moyenne pondérée des polarités des mots-clés détectés, normalisée entre -1 et +1, avec un score neutre (0) si aucun mot-clé n'est détecté (pas d'extrapolation hasardeuse).

**Avantages** : 100% interprétable ("ce score vient de la détection du mot 'profit warning'"), aucun besoin de données d'entraînement, rapide à exécuter (regex/matching de chaînes), facile à corriger quand un cas d'erreur est identifié (on ajuste le poids dans un fichier de config, pas un ré-entraînement).

**Limites assumées** : ne comprend pas la négation ("pas de profit warning prévu" sera mal scoré), ne gère pas le sarcasme ou la nuance contextuelle, dépend entièrement de la qualité du dictionnaire. Acceptable en V1 car le score est **une composante parmi d'autres**, jamais la seule source du signal final, et le score de confiance reflète cette incertitude.

### Niveau 2 (MVP, optionnel selon ressources CPU) — Modèle pré-entraîné généraliste
Utilisation d'un modèle de sentiment financier pré-entraîné et gratuit (ex. FinBERT via `transformers`/HuggingFace) en complément du lexique, comme **second avis**. Si les deux méthodes divergent fortement, le score de confiance est réduit automatiquement (signal contradictoire = moins de certitude affichée). Coût : latence et RAM plus élevés (modèle ~400 Mo), acceptable en job planifié batch (pas en requête HTTP synchrone).

### Niveau 3 (V2) — Fine-tuning ciblé
Si un historique suffisant de couples (article, mouvement de prix réel dans les jours suivants) est accumulé via le backtesting, un modèle de classification (logistic regression ou gradient boosting sur des embeddings TF-IDF, pas un LLM complet) peut être entraîné pour prédire l'impact réel plutôt que la polarité générique. Ce niveau n'est envisagé qu'après preuve, par le backtesting, que les niveaux 1-2 ont une limite de précision mesurée qui justifie l'investissement.

## Extraction de mots-clés

`extract_keywords(text)` fait un matching insensible à la casse et aux accents sur le dictionnaire de niveau 1, avec gestion des variantes morphologiques simples (licencier/licenciement/licenciements via une racine commune ou une petite liste de variantes explicites — pas de stemmer complexe qui introduirait du bruit).

Chaque mot-clé détecté porte :
- son **poids** (force du signal),
- son **horizon d'impact** (un profit warning affecte surtout le court terme ; une acquisition stratégique affecte surtout le moyen/long terme),
- le **nombre d'occurrences** dans l'article (plusieurs mentions renforcent le poids, avec plafond pour éviter qu'un article répétitif ne domine artificiellement le score).

## Impact par horizon : logique de propagation

Le score news d'un horizon donné (`build_feature_vector`, doc 06) agrège les articles des N derniers jours pertinents pour cet horizon, avec une **décroissance temporelle** (un article d'il y a 1 jour pèse plus qu'un article d'il y a 10 jours, pondération exponentielle simple `poids × exp(-jours/demi_vie)`). La demi-vie diffère par horizon : courte pour le court terme (~3 jours), plus longue pour le long terme (~60 jours).

## Pourquoi ne pas utiliser un LLM génératif directement pour scorer/expliquer
Un LLM généraliste peut halluciner un sentiment ou une justification non traçable à un fait précis de l'article — inacceptable pour un outil qui doit justifier chaque signal de façon vérifiable et conforme (doc 17). La stratégie retenue **peut** utiliser un LLM en assistance ponctuelle (V2, ex. reformulation de l'explication déjà calculée pour la rendre plus lisible), mais jamais comme source du score lui-même : le score doit toujours être traçable à des règles ou des features numériques vérifiables.
