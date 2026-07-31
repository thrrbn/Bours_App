FROM python:3.12-slim

WORKDIR /app

# build-essential + libpq-dev : necessaires pour compiler certaines dependances
# Python liees a PostgreSQL. curl : utilise par le healthcheck (Etape 8).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# torch (31/07/2026, bac a sable pedagogique Phase 3 - LSTM asynchrone, voir
# docs/STACK.md) : installe SEPAREMENT depuis l'index PyTorch dedie aux
# wheels CPU-only, AVANT le reste de requirements.txt. Sans cette precaution,
# `pip install torch` depuis l'index PyPI par defaut telecharge la variante
# GPU/CUDA (plusieurs centaines de Mo a plus d'1 Go de bibliotheques NVIDIA
# inutiles ici - aucun GPU sur un usage personnel) - non teste dans son
# integralite lors de l'ecriture de ce Dockerfile : le sandbox de
# developpement utilise pour ce projet n'a pas d'acces reseau vers
# download.pytorch.org (bloque par le proxy sortant). A verifier au premier
# `docker compose up -d --build backend` reel - si l'index est injoignable
# depuis ta machine, retire cette ligne et utilise
# `pip install torch` (sans --index-url) en acceptant le telechargement plus
# lourd de la variante GPU/CUDA.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# --reload est pertinent ici car le compose monte ./backend:/app en volume
# (voir docker-compose.yml) : le code modifie en local est rechargeable a chaud.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
