# Script de deploiement (13/08/2026) - equivalent PowerShell de deploy.sh,
# pour un usage direct depuis Windows (le contexte Docker de ce poste pointe
# vers le NAS - "docker compose ps"/"logs" fonctionnent deja directement en
# PowerShell sans passer par une session SSH). "bash deploy.sh" echoue sur ce
# poste (relais WSL non configure) - ce script fait exactement la meme chose
# en PowerShell natif, sans dependance a bash/WSL.
#
# Usage : depuis ce dossier, en PowerShell : .\deploy.ps1
# (si bloque par la politique d'execution : powershell -ExecutionPolicy Bypass -File deploy.ps1)

Set-Location -Path $PSScriptRoot

Write-Host "=== Reconstruction et redemarrage des conteneurs ===" -ForegroundColor Cyan
docker compose up -d --build
if ($LASTEXITCODE -ne 0) {
    Write-Host "Echec de 'docker compose up -d --build' - arret." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== Etat des conteneurs ===" -ForegroundColor Cyan
docker compose ps

Write-Host ""
Write-Host "=== Derniers logs backend (verifie que les migrations Alembic sont passees) ===" -ForegroundColor Cyan
Start-Sleep -Seconds 3
docker compose logs backend --tail 30

Write-Host ""
Write-Host "=== Termine === (verifie ci-dessus qu'il n'y a pas d'erreur Alembic ni de traceback)" -ForegroundColor Green
