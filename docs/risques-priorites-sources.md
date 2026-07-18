# Les 10 plus grands risques du projet

1. **Rupture d'accès Yahoo Finance** : endpoint non officiel qui change ou se bloque, coupant l'ingestion de prix sans préavis.
2. **Dérive réglementaire** : formulation ou usage qui glisse vers du conseil en investissement de fait, même sans intention (voir doc 17).
3. **Confiance mal placée de l'utilisateur** : un utilisateur qui ignore les disclaimers et traite un signal comme une vérité, malgré les garde-fous produit.
4. **Qualité insuffisante des news gratuites** : flux RSS trop pauvres (titre seul) pour un scoring de sentiment fiable, biaisant le score news.
5. **Sur-ajustement du backtesting** : calibrer les poids/seuils du moteur de règles sur l'historique disponible au point de "tricher" sur les données passées sans généraliser au futur (data snooping).
6. **Charge de maintenance solo** : un développeur seul qui doit gérer ingestion, NLP, scoring, UI, infra et conformité — risque d'épuisement ou de dette technique si le scope MVP n'est pas tenu strictement.
7. **Faux positifs de matching actif/article** : associer une news à un mauvais actif (homonymie) et propager une erreur de score.
8. **Dépendance à un seul serveur** (pas de haute disponibilité) : panne = interruption de service, acceptable en V1 mais à anticiper si l'usage grandit.
9. **Sécurité des données utilisateur** (V2, comptes/watchlists) : toute faille (mot de passe, JWT mal géré) expose des données personnelles sous obligations RGPD.
10. **Explosion de complexité anticipée** : céder à la tentation d'ajouter Celery, microservices, ou un modèle de deep learning avant que le besoin soit mesuré — le risque principal identifié explicitement par le cahier des charges lui-même.

# Les 10 priorités absolues de la V1

1. Un pipeline d'ingestion de prix fiable et idempotent sur un petit nombre d'actifs (10-20), avant toute sophistication.
2. Un moteur de score par règles pondérées, entièrement traçable et testé unitairement.
3. Une explication textuelle non vide et vérifiable pour chaque signal généré — aucune exception.
4. Le disclaimer et le score de confiance visibles partout où un signal apparaît.
5. Un module de backtesting fonctionnel, même simple, pour mesurer objectivement la qualité des signaux avant toute promesse implicite.
6. Une architecture domaine par domaine respectée dès le début (pas de raccourcis "on refactorera plus tard").
7. Des tests unitaires sur le moteur de scoring et le NLP (les deux modules les plus sensibles à l'explicabilité).
8. Un déploiement local reproductible (Docker Compose) avant toute tentative de mise en production.
9. Une liste de mots-clés/poids validée et documentée (base de l'explicabilité NLP), plutôt qu'un modèle boîte noire précoce.
10. Une revue de la formulation produit (vocabulaire des signaux, disclaimers) — idéalement avec un regard juridique — avant toute exposition au-delà d'un usage strictement personnel.

# Les 5 meilleures sources de données pour démarrer à faible coût

1. **Yahoo Finance (via `yfinance` ou endpoints JSON directs)** : gratuit, couverture large (actions belges Euronext Brussels via suffixe `.BR`, actions US/EU), la source la plus réaliste pour démarrer malgré son caractère non officiel.
2. **Flux RSS Yahoo Finance par ticker** : gratuit, simple à parser (`feedparser`), déjà filtré par actif.
3. **Google News RSS filtré par requête** : gratuit, complète la couverture Yahoo, utile notamment pour la presse belge/francophone (recherche "société + bourse" ou "société + Euronext").
4. **Stooq** (`stooq.com`) : source alternative gratuite de prix historiques, utile comme source de secours ou de validation croisée si Yahoo Finance devient instable.
5. **Benzinga (plan de base payant)** : à activer en V2 une fois le budget confirmé — apporte un contenu de news plus riche et structuré (corps d'article complet, tags), mais pas indispensable pour un MVP réellement livrable.
