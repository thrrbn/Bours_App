# Analyste de backtest (LLM local, Ollama)

Outil **autonome**, à lancer depuis ton PC — jamais depuis le NAS, jamais intégré à l'application déployée. Il lit les prix via l'API publique en lecture seule de Bourse Assistant, rejoue un backtest en local, et demande à un modèle de langage local (via [Ollama](https://ollama.com), gratuit et open source) de rédiger une synthèse en français des transactions gagnantes/perdantes et des régimes de marché où la stratégie a le mieux/moins bien fonctionné.

## Pourquoi un outil séparé, et pas une fonctionnalité de l'app

Décision prise le 14/08/2026 (voir l'historique de la conversation) : le NAS Asustor qui héberge l'application n'a pas de GPU, et le projet a déjà pour règle établie de ne jamais faire tourner de calcul lourd en synchrone sur le backend déployé (voir `docs/09-strategie-nlp-sentiment.md`). Faire tourner Ollama sur le NAS serait probablement inutilisable en pratique. Cet outil tourne donc entièrement sur ton PC, et n'écrit jamais rien sur le NAS — il ne fait que lire des prix déjà publics via l'API existante.

Autre principe respecté : les documents `docs/02`, `docs/08` et `docs/09` du projet principal excluent explicitement un LLM comme source de signal ou de score, pour des raisons de traçabilité. Cet outil reste strictement **en aval** d'un backtest déjà terminé — il ne touche jamais au moteur de signal réel, ni aux positions du portefeuille virtuel.

## Ce que fait vraiment le LLM ici (et ce qu'il ne fait pas)

Toute l'analyse "dure" (segmentation par régime de volatilité, comparaison transactions gagnantes/perdantes, plus grosses chutes) est calculée en Python pur, exactement et de façon reproductible, **avant** d'être envoyée au modèle (voir `quant_facts.py`). Le LLM ne "découvre" jamais rien dans les données brutes : son rôle se limite à mettre en récit des faits déjà établis, avec obligation de citer l'identifiant de chaque transaction (`trade_id`) pour toute affirmation. Chaque citation est ensuite vérifiée automatiquement contre les faits réels (`analyst.py::_validate_citations`) — toute transaction citée qui n'existe pas est signalée comme un avertissement dans le rapport final, pas cachée.

En dessous de 15 transactions (`MIN_TRADES_FOR_NARRATIVE` dans `analyst.py`), le rapport reste généré mais affiche un avertissement explicite « échantillon faible » — un backtest perso a souvent entre 5 et 20 transactions par an, ce n'est pas une erreur, juste une limite à garder en tête.

## Limite connue : pas de cours ajusté

L'API publique du NAS (`GET /market-data/{id}/prices`) n'expose pas le cours ajusté des dividendes/splits (`adjusted_close`), contrairement au moteur interne de l'application. Cet outil utilise donc le cours brut — sur un titre versant des dividendes réguliers, les résultats peuvent différer légèrement (quelques % de rendement sur plusieurs années) de ceux affichés par "tester les paramètres" dans l'app. Ce n'est pas un bug.

## Stratégies supportées

Seulement les 5 stratégies auto-suffisantes (prix seuls, aucune donnée stockée côté application) : `sma_cross`, `rsi_mean_reversion`, `macd_cross`, `bollinger_reversion`, `buy_and_hold`. `signal_replay` et le moteur interne (`internal_rules`) sont hors périmètre v1 : ils dépendent de signaux déjà calculés côté NAS, non exposés par l'API publique en lecture seule (voir `strategies.py` pour le détail).

## Installation

1. Installer [Ollama](https://ollama.com) sur ton PC.
2. Télécharger un modèle (ex. `ollama pull llama3.1` — compter ~4,7 Go, ou un modèle plus léger comme `ollama pull mistral` si ton PC a peu de RAM).
3. Dans ce dossier :
   ```
   pip install -r requirements.txt
   ```

## Utilisation

```
python cli.py --url http://<ip-du-nas>:8082 --ticker MC.PA \
    --strategy rsi_mean_reversion --start 2025-01-01 --end 2026-08-01
```

Le port `8082` est celui exposé par le NAS (voir `docker-compose.yml` — le conteneur backend écoute en interne sur 8000, mappé sur 8082 côté hôte).

Options utiles :
- `--model` : modèle Ollama à utiliser (défaut `llama3.1`).
- `--out rapport.md` : écrit le rapport dans un fichier au lieu de l'afficher.
- `--no-cache` : force un nouvel appel au modèle même si un résultat identique est déjà en cache.

Le premier appel pour une combinaison donnée (mêmes faits + même modèle) interroge réellement Ollama, ce qui peut prendre de quelques secondes à plusieurs minutes selon ton PC et le modèle choisi. Les appels suivants avec les mêmes données ressortent instantanément du cache disque (`.cache/`, jamais versionné — voir `.gitignore`).

## Structure du code

| Fichier | Rôle |
|---|---|
| `llm_provider.py` | Interface abstraite + `OllamaProvider` (appel HTTP local, mode JSON, température 0) + `MockProvider` (tests sans Ollama) + cache disque. |
| `strategies.py` | Copie volontaire des stratégies pures de `kernc_engine.py` — pas d'import direct pour éviter toute dépendance à la config du backend (voir commentaire en tête de fichier). |
| `api_client.py` | Client HTTP en lecture seule vers l'API du NAS (résolution de ticker, historique de prix). |
| `backtest_runner.py` | Rejoue le backtest en local pour accéder aux transactions individuelles et à la courbe de capital (données que l'app ne persiste pas). |
| `quant_facts.py` | Tous les calculs statistiques purs, sans LLM — segmentation par régime, caractérisation des pertes, pires épisodes de repli. |
| `analyst.py` | Construit le prompt, appelle le LLM, valide les citations, génère le rapport Markdown final. |
| `cli.py` | Point d'entrée en ligne de commande. |

## Ce qui n'est volontairement pas fait dans cette première version

Le générateur de classes `TradingStrategy` à partir d'une description en français (évoqué dans la proposition initiale) n'est pas construit ici — à traiter séparément si utile, avec un bac à sable d'exécution restreint pour le code généré (jamais un `exec()` du code du LLM tel quel).
