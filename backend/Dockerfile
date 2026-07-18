FROM python:3.12-slim

WORKDIR /app

# build-essential + libpq-dev : necessaires pour compiler certaines dependances
# Python liees a PostgreSQL. curl : utilise par le healthcheck (Etape 8).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# --reload est pertinent ici car le compose monte ./backend:/app en volume
# (voir docker-compose.yml) : le code modifie en local est rechargeable a chaud.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
