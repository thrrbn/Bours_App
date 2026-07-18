# 5. Schéma PostgreSQL — explication

Le DDL complet est dans `05-schema-postgresql.sql`. En production, les tables sont créées via les migrations Alembic générées à partir des modèles SQLAlchemy — ce fichier SQL est la documentation de référence, pas la source de vérité opérationnelle.

## Vue relationnelle simplifiée

```
users ──< user_watchlist_items >── assets ──< price_bars
                                       │  │
                                       │  └──< technical_indicators
                                       │
                                       └──< news_articles ──< news_keyword_matches
                                       │
                                       └──< signals ──< signal_explanations
                                              │
                                              └──< backtest_results >── backtest_runs

compliance_audit_log : table transverse, référence libre (entity_type, entity_id)
```

## Décisions de modélisation et justification

**UUID comme clé primaire** pour les entités métier (`assets`, `users`, `signals`...) plutôt que des entiers auto-incrémentés : évite les collisions si un jour les données sont fusionnées entre environnements (local/prod) ou exportées vers un autre système (intégration future au stack de référence). Coût : légèrement plus lourd en stockage/index, acceptable au volume visé (quelques milliers d'actifs, pas des milliards de lignes).

**`price_bars` et `technical_indicators` séparés** plutôt qu'une seule table large : les indicateurs techniques peuvent être recalculés (changement de méthode, ex. passage RSI 14 à RSI 21) sans toucher aux données sources immuables (prix). Cela respecte aussi le principe d'explicabilité : on peut recalculer `technical_indicators` avec une nouvelle version de logique et versionner le changement, tout en gardant `price_bars` comme unique source de vérité des prix.

**`signals` + `signal_explanations` séparés** (et non une colonne JSON unique dans `signals`) : chaque composante du score (technique, news, risque) doit pouvoir être interrogée, filtrée et affichée indépendamment dans l'UI ("montre-moi uniquement la contribution news"). Le champ `supporting_data JSONB` dans `signal_explanations` garde la flexibilité d'ajouter de nouvelles données de support sans migration de schéma à chaque nouvelle feature.

**`engine_version` sur `signals` et `backtest_runs`** : traçabilité obligatoire — un signal généré par les règles pondérées V1 n'a pas la même nature statistique qu'un signal généré par un modèle de gradient boosting V2. Ne jamais mélanger ces générations dans un même calcul de performance sans le savoir explicitement (c'est aussi une exigence de gouvernance du risque, doc 07/17).

**`compliance_audit_log` générique** (`entity_type` + `entity_id` plutôt que des clés étrangères strictes) : ce journal doit pouvoir tracer des événements sur n'importe quelle entité présente ou future (signal affiché, disclaimer montré, news ingérée) sans multiplier les tables d'audit dédiées.

**Index** : posés sur les colonnes de filtrage/tri les plus fréquentes (par actif + date décroissante pour les séries temporelles, par horizon pour les signaux). Pas d'index prématuré sur des colonnes peu interrogées — à ajuster une fois l'usage réel observé (`EXPLAIN ANALYZE` avant d'ajouter un index, pas par principe).

**Contraintes d'unicité** : `(asset_id, trade_date)` sur `price_bars` et `technical_indicators` empêche les doublons d'ingestion (idempotence du job quotidien). `(url)` unique sur `news_articles` empêche de ré-ingérer deux fois le même article vu par deux flux RSS différents.

## Ce que ce schéma ne fait pas (volontairement, en V1)
- Pas de partitionnement de table (inutile avant plusieurs dizaines de millions de lignes).
- Pas de table de fondamentaux financiers dédiée (P/E, dette/capitaux propres) — prévu en V2 quand une source fiable est choisie.
- Pas de table de portefeuille réel (positions, transactions) — hors scope produit (voir doc 01, "ce que l'application n'est pas").
