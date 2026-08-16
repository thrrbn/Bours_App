# tools/shared/

Code partagé entre les outils autonomes PC/Mac de `tools/` (voir `docs/19-outils-pc-autonomes.md` pour le principe général). Pas un outil en soi — rien à lancer directement ici.

## Contenu

| Fichier | Rôle |
|---|---|
| `nas_api_client.py` | `BourseApiClient` : client HTTP en lecture seule vers l'API publique du NAS (résolution de ticker, historique de prix, liste des actifs suivis). |

## Comment un outil l'utilise

Chaque outil ajoute le dossier `tools/shared/` à son `sys.path` avant d'importer (voir `backtest_analyst/cli.py` pour l'exemple de référence) :

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "shared"))
from nas_api_client import BourseApiClient, ApiClientError
```
