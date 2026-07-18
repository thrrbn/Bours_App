# 8. Pipeline de collecte de news et marché

## Vue d'ensemble du flux quotidien

```
06:00  ingest_prices_job   → pour chaque asset actif : fetch historique manquant (Yahoo Finance)
                             → upsert price_bars → compute_indicators → upsert technical_indicators
06:30  ingest_news_job     → pour chaque asset actif : fetch flux RSS (Yahoo/Google News filtré ticker)
                             → dédup par URL → score_sentiment + extract_keywords → upsert news_articles/matches
07:00  compute_signals_job → pour chaque asset actif, pour chaque horizon (short/medium/long) :
                             → build_feature_vector → engine.compute() → persist signals + explanations
```

Ces jobs tournent via APScheduler (voir doc 14), séquencés (news et prix doivent être ingérés avant le calcul des signaux). En V1, le volume (dizaines à centaines d'actifs) permet un traitement séquentiel simple ; le parallélisme (asyncio.gather par lot de N tickers) est ajouté seulement si la durée totale dépasse une fenêtre acceptable (mesuré, pas anticipé).

## Ingestion de prix (Yahoo Finance)

**Contrainte connue** : Yahoo Finance n'a pas d'API officielle publique et documentée. Deux options réalistes :
1. **`yfinance`** (librairie Python communautaire) — la plus simple à démarrer, mais dépend d'un endpoint non contractuel qui peut changer sans préavis.
2. **Appel direct `httpx`** sur les endpoints JSON internes utilisés par le site (`query1.finance.yahoo.com/...`) — plus de contrôle mais même fragilité.

**Décision** : démarrer avec `yfinance` (implémentation la plus rapide), **encapsulé derrière l'interface `MarketDataProvider`** (doc 06). Si l'endpoint casse ou si les limites de débit deviennent bloquantes, le remplacement se fait dans un seul fichier (`providers/yahoo_finance.py`) sans toucher au reste du domaine. C'est précisément la raison d'être de l'abstraction provider.

**Gestion des pannes** : retry avec backoff exponentiel (3 tentatives), logging systématique des échecs, le job continue sur les autres actifs si un ticker échoue (pas d'arrêt global sur une erreur isolée).

**Idempotence** : la contrainte unique `(asset_id, trade_date)` permet un upsert sûr — relancer le job deux fois dans la même journée ne crée pas de doublons.

## Ingestion de news (flux RSS gratuits)

**Sources V1** :
- Flux RSS Yahoo Finance par ticker (`https://finance.yahoo.com/rss/headline?s=TICKER`).
- Google News RSS filtré par requête (`https://news.google.com/rss/search?q=TICKER+bourse`).

**Traitement** :
1. Parsing RSS (`feedparser`).
2. Déduplication stricte par URL (contrainte unique en base).
3. Association à l'actif : matching par ticker/nom dans le titre (V1, simple) — un faux positif possible si le nom est ambigu (ex. "Solvay" société vs "solvant" mot commun), accepté en V1 et amélioré en V2 par NER (doc 09).
4. Scoring de sentiment + extraction de mots-clés (voir doc 09) appliqués au titre + résumé disponible dans le flux RSS (le contenu complet de l'article n'est généralement pas dans le flux gratuit, limite connue — voir doc 17).

**Benzinga (V2)** : si un plan payant abordable est confirmé, il remplace/complète les flux RSS avec un contenu plus riche (corps d'article complet, tags structurés, ratings d'analystes). L'intégration se fait comme un second `NewsProvider` implémentant la même interface — aucun changement requis dans `service.py` ou dans la couche NLP.

## Pipeline de calcul des signaux

1. `build_feature_vector(asset, horizon, as_of_date)` lit les derniers `technical_indicators` et agrège le `news_articles`/`news_keyword_matches` sur une fenêtre glissante dépendante de l'horizon (ex. 5 jours pour le court terme, 30 jours pour le moyen terme, 180 jours pour le long terme).
2. `engine.compute(features)` applique le modèle actif (règles pondérées V1) et retourne un `SignalResult` structuré (scores + composantes).
3. Le moteur génère les explications textuelles par template déterministe (pas de génération libre par LLM en V1 — évite les hallucinations et les problèmes de conformité, voir doc 11).
4. `guardrails.validate_signal_wording()` (domaine compliance) valide le texte avant persistance : si un terme interdit apparaît (bug de template), le signal est rejeté et loggé en erreur plutôt que publié avec une formulation non conforme.
5. Persistance dans `signals` + `signal_explanations`.

## Schéma de résilience globale
- Chaque étape du pipeline est **idempotente** (peut être rejouée sans effet de bord dupliqué).
- Chaque étape est **indépendante en échec** : une erreur sur l'ingestion news d'un actif ne bloque pas le calcul de signal technique pour les autres actifs (le score news sera simplement absent/dégradé, ce qui réduit le score de confiance affiché — voir doc 11).
- Tout est **journalisé** dans les logs applicatifs et, pour les événements significatifs (signal généré, erreur d'ingestion), dans `compliance_audit_log`.
