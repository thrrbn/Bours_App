#!/bin/bash
# Script de deploiement unique (01/08/2026) - a lancer SUR LE NAS, depuis le
# dossier du projet, apres avoir recopie les fichiers modifies (SMB/WinSCP ou
# git pull). Remplace la sequence manuelle "docker compose up -d --build"
# puis "penser a lancer alembic upgrade head" (etape qui a deja ete oubliee
# une fois - voir backend/entrypoint.sh, qui applique desormais les
# migrations automatiquement au demarrage du conteneur backend).
#
# Usage : sudo bash deploy.sh, DEPUIS UNE SESSION SSH SUR LE NAS.
# ("bash deploy.sh" plutot que "./deploy.sh" : evite de dependre du bit
# executable, qui peut se perdre lors d'une copie depuis Windows. "sudo" :
# necessaire tant que l'utilisateur admin n'est pas dans le groupe docker
# sur ce NAS, voir historique de deploiement.)
#
# 13/08/2026 : depuis un poste Windows dont le contexte Docker pointe deja
# vers le NAS (docker compose fonctionne directement en PowerShell sans SSH),
# utiliser deploy.ps1 a la place - "bash deploy.sh" echoue sur un Windows
# sans WSL correctement configure (erreur "execvpe(/bin/bash) failed").
set -e

cd "$(dirname "$0")"

echo "=== Reconstruction et redemarrage des conteneurs ==="
docker compose up -d --build

echo
echo "=== Etat des conteneurs ==="
docker compose ps

echo
echo "=== Derniers logs backend (verifie que les migrations Alembic sont passees) ==="
sleep 3
docker compose logs backend --tail 30

echo
echo "=== Termine === (verifie ci-dessus qu'il n'y a pas d'erreur Alembic ni de traceback)"
