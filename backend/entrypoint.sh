#!/bin/sh
# Point d'entree du conteneur backend (01/08/2026) : applique les migrations
# Alembic AVANT de demarrer le serveur, a chaque (re)demarrage du conteneur.
# Objectif : ne plus jamais avoir a se souvenir de lancer
# "alembic upgrade head" manuellement apres un redeploiement (bug reel
# rencontre le 01/08/2026 - migration 0009 non appliquee, backtests en echec
# silencieux cote utilisateur). Idempotent : si tout est deja a jour,
# Alembic ne fait rien et l'affiche ("target database is up to date").
#
# Invoque via "sh entrypoint.sh" (voir Dockerfile) plutot que via le bit
# executable + shebang : ce fichier vit dans ./backend, monte en volume
# bind (voir docker-compose.yml) - une copie depuis Windows (SMB/WinSCP)
# ne preserve pas toujours les permissions Unix, "sh entrypoint.sh" evite
# ce piege.
set -e

# 13/08/2026 : bug reel observe sur le NAS juste apres l'ajout de ce script -
# le premier "alembic upgrade head" echouait avec
# "socket.gaierror: [Errno -2] Name or service not known" en resolvant
# l'hote "db" : malgre "depends_on: condition: service_healthy" (voir
# docker-compose.yml), le DNS interne Docker n'etait pas encore pret au tout
# premier instant du demarrage du conteneur backend (course au demarrage
# apres un "docker compose up -d --build" qui recree le reseau). Avec
# "set -e" seul, ce echec faisait sortir le script et donc tout le
# conteneur - `restart: unless-stopped` le relancait en boucle jusqu'a ce
# que le DNS finisse par etre pret, mais avec une app indisponible pendant
# ce temps. Boucle de nouvelle tentative ci-dessous : tolere ce genre de
# course transitoire au lieu de compter sur les redemarrages du conteneur
# entier.
echo "[entrypoint] Application des migrations Alembic..."
attempt=1
max_attempts=10
until alembic upgrade head; do
  if [ "$attempt" -ge "$max_attempts" ]; then
    echo "[entrypoint] Echec des migrations Alembic apres $max_attempts tentatives - abandon."
    exit 1
  fi
  echo "[entrypoint] Migration Alembic echouee (tentative $attempt/$max_attempts) - nouvel essai dans 3s..."
  attempt=$((attempt + 1))
  sleep 3
done
echo "[entrypoint] Migrations a jour."

echo "[entrypoint] Demarrage du serveur..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
