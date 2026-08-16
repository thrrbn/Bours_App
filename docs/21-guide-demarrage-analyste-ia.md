# Guide de démarrage — Analyste IA en local (Windows et macOS)

Guide pratique, complémentaire à `docs/20-instance-locale-pc-mac.md` (qui explique *pourquoi* cette architecture existe). Ici : uniquement les commandes, dans l'ordre, pour les deux systèmes utilisés — PC Windows et MacBook (Apple Silicon M4).

## Principe à garder en tête

Il faut **deux programmes qui tournent en même temps, dans deux fenêtres de terminal séparées, qu'on ne ferme jamais tant qu'on utilise l'app** :

- **Terminal A** : le backend (`uvicorn`) — répond aux données, aux calculs, à l'analyste IA.
- **Terminal B** : le frontend (`npm run dev`) — sert les pages web dans le navigateur.

Chacun de ces deux programmes **bloque** son terminal (il reste affiché et attend, sans rendre la main) : si on veut taper une autre commande, il faut une **troisième fenêtre**, jamais réutiliser A ou B. C'est la source de la majorité des blocages : un terminal fermé par erreur = un des deux serveurs qui s'arrête sans prévenir.

Port choisi pour le backend local dans ce guide : **8010** (pas 8000, pour éviter un conflit si un autre projet tourne déjà dessus — cas fréquent avec Docker Desktop qui garde des conteneurs actifs en arrière-plan).

---

## Windows (PC)

### Prérequis (une seule fois)

- [Python 3.12](https://www.python.org/downloads/) — cocher "Add python.exe to PATH" à l'installation.
- [Node.js LTS](https://nodejs.org/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) — pour la base de données locale.
- [Ollama](https://ollama.com) — tourne automatiquement en arrière-plan après installation.

### Installation (une seule fois)

**1. Base de données locale**

```powershell
cd C:\Users\tboen\Documents\Document_Asus\bourse-app
docker compose up -d db
```

**2. Backend**

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Ouvre `backend\.env` et vérifie/ajoute (**une seule fois chaque ligne** — un `.env` avec une même clé écrite deux fois garde la *dernière* valeur, source d'un bug déjà rencontré) :

```
DB_HOST=localhost
DB_PORT=5433
ENABLE_LLM_ANALYST=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1
```

```powershell
alembic upgrade head
```

**3. Modèle Ollama**

```powershell
ollama pull llama3.1
```

**4. Frontend**

```powershell
cd ..\frontend
npm install
```

**5. Peupler des données de test**

Garder le backend lancé (voir "Démarrage" ci-dessous) puis, dans un troisième terminal :

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8010/api/v1/maintenance/seed-bel20
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8010/api/v1/maintenance/refresh-all
```

### Démarrage (à chaque session)

**Terminal A — backend, à laisser ouvert :**

```powershell
cd C:\Users\tboen\Documents\Document_Asus\bourse-app\backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8010
```

Attendre la ligne `Application startup complete.`

**Terminal B — frontend, à laisser ouvert :**

```powershell
cd C:\Users\tboen\Documents\Document_Asus\bourse-app\frontend
$env:VITE_API_TARGET = "http://127.0.0.1:8010"
npm run dev
```

Noter le port affiché (`Local: http://localhost:XXXX/`) — Vite change de port tout seul si 5173 est déjà pris par un autre projet. Ouvrir cette adresse dans le navigateur.

### Pièges déjà rencontrés (Windows)

| Symptôme | Cause | Solution |
|---|---|---|
| `{"detail":"Not Found"}` sur toutes les routes, même `/health` | Un **autre** programme (souvent un conteneur Docker d'un autre projet) écoute déjà sur le port utilisé | `docker ps -a`, repérer le conteneur sur ce port, ou changer de port avec `--port` |
| `localhost` ne répond pas mais `127.0.0.1` non plus | `localhost` peut résoudre en IPv6 (`::1`) alors qu'un service tiers y écoute — vérifier avec `Get-NetTCPConnection -LocalPort <port> -State Listen` puis `Get-Process -Id <PID>` | Toujours utiliser `127.0.0.1` explicitement pour les tests directs |
| `enabled:false` sur `/llm-analyst/status` alors que `.env` semble correct | Clé `ENABLE_LLM_ANALYST` présente deux fois dans `.env` | Ouvrir `.env`, ne garder qu'une seule occurrence à `true`, redémarrer `uvicorn` |
| `npm error Invalid Version` | `node_modules` créé sur un autre système d'exploitation (binaires incompatibles) | `Remove-Item -Recurse -Force node_modules`, `Remove-Item package-lock.json`, `npm install` |
| Le lien "Analyste IA" n'apparaît pas alors que tout semble correct | Page pas rechargée après redémarrage du backend, ou `VITE_API_TARGET` reperdue (ne survit pas d'un terminal à l'autre) | `Ctrl+Shift+R` dans le navigateur ; sinon relancer `npm run dev` avec `$env:VITE_API_TARGET` redéfinie juste avant |
| `ECONNREFUSED` dans les logs Vite | Le terminal du backend a été fermé (ou réutilisé pour une autre commande) | Rouvrir un terminal dédié et relancer `uvicorn` (voir "Démarrage") |

---

## macOS (MacBook, Apple Silicon M4)

### Prérequis (une seule fois)

Avec [Homebrew](https://brew.sh) déjà installé :

```bash
brew install python@3.12 node
brew install --cask docker ollama
```

Lancer Docker Desktop et Ollama une première fois depuis le Launchpad (chacun ajoute son icône dans la barre de menu). Le M4 fait tourner Ollama nativement en accéléré (Metal) — pas de configuration particulière nécessaire, généralement plus rapide qu'un PC sans GPU dédié.

### Installation (une seule fois)

**1. Base de données locale**

```bash
cd ~/Document_Asus/bourse-app   # adapter selon l'emplacement réel du dossier sur ce Mac
docker compose up -d db
```

**2. Backend**

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Ouvre `backend/.env` (`nano .env` ou dans un éditeur de texte) et vérifie/ajoute (**une seule fois chaque ligne**) :

```
DB_HOST=localhost
DB_PORT=5433
ENABLE_LLM_ANALYST=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1
```

```bash
alembic upgrade head
```

**3. Modèle Ollama**

```bash
ollama pull llama3.1
```

**4. Frontend**

```bash
cd ../frontend
npm install
```

**5. Peupler des données de test**

Garder le backend lancé (voir "Démarrage" ci-dessous) puis, dans un troisième terminal :

```bash
curl -X POST http://127.0.0.1:8010/api/v1/maintenance/seed-bel20
curl -X POST http://127.0.0.1:8010/api/v1/maintenance/refresh-all
```

(`curl` sur macOS est le vrai `curl`, pas un alias piégeux comme sur Windows — pas de souci particulier ici.)

### Démarrage (à chaque session)

**Terminal A — backend, à laisser ouvert :**

```bash
cd ~/Document_Asus/bourse-app/backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8010
```

Attendre la ligne `Application startup complete.`

**Terminal B — frontend, à laisser ouvert :**

```bash
cd ~/Document_Asus/bourse-app/frontend
export VITE_API_TARGET="http://127.0.0.1:8010"
npm run dev
```

Noter le port affiché (`Local: http://localhost:XXXX/`) et l'ouvrir dans le navigateur.

Astuce Terminal.app/iTerm2 : `Cmd+T` ouvre un nouvel onglet dans la même fenêtre — pratique pour garder A et B visibles côte à côte sans multiplier les fenêtres.

### Pièges à surveiller (macOS)

Les mêmes principes qu'sous Windows s'appliquent, avec ces équivalences :

| Sur Windows | Équivalent macOS |
|---|---|
| `Get-NetTCPConnection -LocalPort 8010 -State Listen` | `lsof -i :8010` |
| `Get-Process -Id <PID>` | `ps -p <PID>` |
| `$env:VITE_API_TARGET = "..."` | `export VITE_API_TARGET="..."` (ne survit pas non plus d'un terminal à l'autre) |
| `.venv\Scripts\Activate.ps1` | `source .venv/bin/activate` |
| Clé dupliquée dans `.env` | Même piège, même solution (garder une seule occurrence) |

Point d'attention propre à macOS : **AirPlay Receiver** utilise le port 5000 par défaut (pas utilisé ici, mais un classique si un jour un service tourne dessus) — à désactiver dans Réglages Système → Général → AirDrop et Handoff si jamais besoin de ce port.

---

## Utilisation (une fois les deux terminaux lancés, sur les deux systèmes)

1. Ouvrir l'adresse affichée par le terminal frontend (`http://localhost:XXXX/`).
2. Vérifier que le lien **"Analyste IA"** apparaît dans le menu — sinon, tester directement `http://127.0.0.1:8010/api/v1/llm-analyst/status` dans le navigateur : doit répondre `{"enabled":true,...}`.
3. Aller sur la page, choisir un actif déjà importé, une stratégie, une période, cliquer sur "Lancer l'analyse".
4. Le premier appel à un modèle donné peut prendre plusieurs minutes ; les suivants avec les mêmes paramètres ressortent instantanément du cache disque (`backend/.cache/llm_analyst/`, jamais versionné).

Pour arrêter proprement : `Ctrl+C` dans chacun des deux terminaux A et B.
