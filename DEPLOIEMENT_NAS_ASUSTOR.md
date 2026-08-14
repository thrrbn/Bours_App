# Déploiement NAS Asustor (`admin@AS5404T-B13C:/volume1/Docker/bourse_app`)

Procédure documentée le 14/08/2026, après la première mise en place réelle du flux git sur ce NAS. Même principe que le GMAO : le poste de dev (`C:\Users\tboen\Documents\Document_Asus\bourse-app`) fait push/pull complet vers `github.com/thrrbn/Bours_App`, le NAS ne fait **que du pull** via une deploy key GitHub en lecture seule.

## Mise à jour courante (le cas normal)

Depuis une session SSH sur le NAS :

```bash
cd /volume1/Docker/bourse_app
git pull
sudo bash deploy.sh
```

`deploy.sh` reconstruit les images si besoin, redémarre les conteneurs et affiche les derniers logs du backend pour vérifier visuellement que les migrations Alembic sont passées sans erreur (voir sa propre en-tête de commentaire pour le détail). Depuis un poste Windows dont le contexte Docker pointe déjà vers ce NAS (pas de SSH nécessaire), utiliser `deploy.ps1` à la place — équivalent PowerShell du même script.

## Appliquer/vérifier une migration Alembic sans tout redémarrer

```bash
sudo docker exec bourse_backend sh -c "cd /app && alembic upgrade head"
```

**Pourquoi ça peut être nécessaire séparément de `deploy.sh`** : `docker-compose.yml` monte `./backend` et `./frontend` en bind mount, donc un simple `git pull` suffit à mettre à jour le code Python/Vue déjà pris en compte à chaud par les conteneurs en cours d'exécution (`uvicorn --reload` / HMR Vite) — mais une **nouvelle migration Alembic ne s'applique automatiquement qu'au (re)démarrage du conteneur backend** (voir `backend/entrypoint.sh`, qui lance `alembic upgrade head` avant `uvicorn` à chaque démarrage). Après un `git pull` qui ajoute une migration sans relancer `deploy.sh` juste après, la base reste donc en retard tant qu'on n'a pas soit redémarré le conteneur (`docker compose restart backend` ou `deploy.sh`), soit lancé la commande ci-dessus à la main.

`alembic` n'existe que **dans le conteneur** backend (dépendance Python de `backend/requirements.txt`) — jamais accessible en direct sur le shell du NAS (`-sh: alembic: not found` si on essaie), toujours via `docker exec bourse_backend ...`.

## Configuration SSH (déjà en place — pour référence ou réinstallation sur un NAS neuf)

Deploy key GitHub dédiée, **lecture seule** (jamais "Allow write access"), générée sur le poste de dev et transférée manuellement sur le NAS (jamais recréée côté NAS) :

- Clé publique ajoutée dans GitHub → repo `Bours_App` → Settings → Deploy keys.
- Clé privée (`bourse_app_nas_deploy`) placée à la racine du repo (`/volume1/Docker/bourse_app/`, pas dans `~/.ssh`, par choix — exclue du suivi git via `.gitignore`), permissions `600`.
- `~/.ssh/config` sur le NAS :
  ```
  Host github.com-bourse_app
      HostName github.com
      User git
      IdentityFile /volume1/Docker/bourse_app/bourse_app_nas_deploy
      IdentitiesOnly yes
  ```
- Remote du repo configuré pour passer par cet alias :
  ```bash
  git remote set-url origin git@github.com-bourse_app:thrrbn/Bours_App.git
  ```
- Vérification : `ssh -T github.com-bourse_app` doit répondre *"Hi thrrbn/Bours_App! You've successfully authenticated, but GitHub does not provide shell access."*

## Pièges déjà rencontrés (14/08/2026)

- **`fatal: not a git repository (or any parent up to mount point /)`** en lançant `git remote add`/`git fetch`/`git checkout` juste après `git init` sur un dossier déjà peuplé : en réalité un message de "dubious ownership" masqué par un fetch réussi juste avant — le dossier appartenait à un autre utilisateur que celui lançant la commande. Fix :
  ```bash
  git config --global --add safe.directory /volume1/Docker/bourse_app
  ```
- **`error: The following untracked working tree files would be overwritten by checkout`** : le dossier contenait déjà une copie complète du projet (déposée à la main avant la mise en place de git), donc `git checkout -b main origin/main` refuse d'écraser ces fichiers non suivis. Fix utilisé une seule fois, à l'installation initiale (pas nécessaire pour les mises à jour suivantes, qui partent d'un dépôt déjà propre) :
  ```bash
  tar czf /volume1/Docker/bourse_app_backup_$(date +%Y%m%d%H%M).tar.gz -C /volume1/Docker bourse_app
  git branch -m main
  git fetch origin
  git reset --hard origin/main
  ```
  `reset --hard` écrase les fichiers suivis par le dépôt mais laisse intacts ceux qui n'en font pas partie (`.env`, la clé de déploiement...) — la sauvegarde `tar` reste une sécurité en plus.
- **`permission denied while trying to connect to the Docker daemon socket`** : l'utilisateur `admin` n'est pas dans le groupe `docker` sur ce NAS. Préfixer les commandes Docker par `sudo`, ou ajouter `admin` au groupe `docker` via DSM (Panneau de configuration → Utilisateur et groupe → Groupe → `docker`) puis se reconnecter en SSH.
- **`-sh: alembic: not found`** : voir section ci-dessus — toujours passer par `docker exec bourse_backend ...`.
