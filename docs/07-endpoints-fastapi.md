# 7. Endpoints FastAPI

Toutes les routes sont préfixées `/api/v1`. Authentification par JWT (Bearer token) sur toutes les routes sauf `auth/login`, `auth/register` et les endpoints de santé.

## Auth (`domains/users`)
| Méthode | Route | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Créer un compte (V1 : usage local/admin uniquement) |
| POST | `/api/v1/auth/login` | Authentification, retourne un JWT |
| GET | `/api/v1/auth/me` | Profil de l'utilisateur courant |

## Assets (`domains/assets`)
| Méthode | Route | Description |
|---|---|---|
| GET | `/api/v1/assets` | Liste des actifs suivis, filtrable par `market`, `sector` |
| GET | `/api/v1/assets/search?q=` | Recherche par ticker ou nom |
| GET | `/api/v1/assets/{asset_id}` | Détail d'un actif + métadonnées |
| POST | `/api/v1/assets` | Ajouter un actif au référentiel (admin) |
| POST | `/api/v1/assets/{asset_id}/watch` | Ajouter à la watchlist de l'utilisateur courant |

## Market data (`domains/market_data`)
| Méthode | Route | Description |
|---|---|---|
| GET | `/api/v1/market-data/{asset_id}/prices?start=&end=` | Historique de prix/volumes |
| GET | `/api/v1/market-data/{asset_id}/indicators?start=&end=` | Indicateurs techniques calculés |
| POST | `/api/v1/market-data/{asset_id}/refresh` | Force une ré-ingestion (usage debug/admin) |

## News (`domains/news`)
| Méthode | Route | Description |
|---|---|---|
| GET | `/api/v1/news/{asset_id}?limit=` | Articles récents pour un actif |
| GET | `/api/v1/news/{asset_id}/sentiment-summary` | Sentiment agrégé + mots-clés dominants sur une période |

## Signals (`domains/signals`)
| Méthode | Route | Description |
|---|---|---|
| GET | `/api/v1/signals/{asset_id}?horizon=short\|medium\|long` | Signal courant avec explication complète |
| GET | `/api/v1/signals/{asset_id}/history?horizon=&start=&end=` | Historique des signaux |
| POST | `/api/v1/signals/{asset_id}/recompute` | Force un recalcul (usage debug/admin) |

## Backtests (`domains/backtests`)
| Méthode | Route | Description |
|---|---|---|
| POST | `/api/v1/backtests/run` | Lance un backtest sur une période/scope d'actifs |
| GET | `/api/v1/backtests/{run_id}` | Résultats agrégés d'un run |
| GET | `/api/v1/backtests/{run_id}/details/{asset_id}` | Détail par actif |

## Compliance (`domains/compliance`)
| Méthode | Route | Description |
|---|---|---|
| GET | `/api/v1/compliance/disclaimer` | Texte légal à afficher (source unique pour le frontend) |

## Santé / observabilité
| Méthode | Route | Description |
|---|---|---|
| GET | `/api/v1/health` | Liveness (process up) |
| GET | `/api/v1/health/ready` | Readiness (DB joignable) |

## Format de réponse standard pour un signal (contrat `SignalRead`)

```json
{
  "asset": {"ticker": "SOLB.BR", "name": "Solvay", "market": "EURONEXT_BRUSSELS"},
  "horizon": "short",
  "computed_at": "2026-07-10T18:00:00Z",
  "scores": {
    "technical": 42.0,
    "news": 58.0,
    "risk": 35.0,
    "confidence": 71.0
  },
  "final_signal": "surveillance",
  "explanations": [
    {
      "component": "technical",
      "contribution_pct": 55.0,
      "text": "Le RSI (14 jours) est à 38, proche de la zone de survente, et le prix est passé sous sa moyenne mobile 20 jours il y a 3 séances.",
      "supporting_data": {"rsi_14": 38.2, "sma_20_cross": "below"}
    },
    {
      "component": "news",
      "contribution_pct": 45.0,
      "text": "2 articles publiés ces 5 derniers jours mentionnent une 'guidance' revue à la baisse, impact estimé sur l'horizon court terme.",
      "supporting_data": {"keyword": "guidance", "sentiment": -0.42}
    }
  ],
  "disclaimer": "Ce signal est un score statistique, pas un conseil en investissement. Voir /api/v1/compliance/disclaimer."
}
```

Ce contrat garantit qu'**aucun signal n'est renvoyé sans son tableau `explanations` non vide** — contrainte imposée au niveau du schéma Pydantic de sortie (validation qui échoue si `explanations` est vide), pas seulement une convention de code.
