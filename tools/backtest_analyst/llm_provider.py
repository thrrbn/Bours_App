"""
Chantier 0 (14/08/2026) : interface LLM abstraite + implementation Ollama.

Decision explicite (voir README.md de ce dossier) : cet outil est
volontairement AUTONOME et separe de l'application deployee sur le NAS -
il tourne sur le PC de l'utilisateur, jamais sur le NAS lui-meme (pas de
GPU disponible la-bas, et le projet principal a deja pour regle etablie de
ne jamais faire tourner de calcul lourd en synchrone - voir
backend/docs/09-strategie-nlp-sentiment.md). Aucun code de ce dossier n'est
importe par `backend/app`, et reciproquement.

Sans cache, aucune analyse impliquant un LLM n'est reproductible ni
economiquement viable (chaque re-execution recalculerait tout, meme pour
rejouer un rapport deja genere) - le cache disque ci-dessous est donc une
partie integrante de l'abstraction, pas une optimisation secondaire.

Contrat commun a tous les providers : `complete()` prend un prompt et un
JSON Schema optionnel, retourne un dict Python deja parse (jamais une
chaine JSON brute a re-parser cote appelant). Temperature fixee a 0 partout
- ce n'est pas un outil de creativite, on veut la sortie la plus
deterministe possible pour une meme entree (le cache s'appuie d'ailleurs
sur cette hypothese : deux appels avec le meme prompt/modele DEVRAIENT, en
theorie, produire la meme reponse - meme si en pratique un LLM n'est jamais
strictement deterministe bit a bit, d'ou l'interet du cache qui fige le
premier resultat obtenu plutot que d'esperer une reproductibilite parfaite
cote modele).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent / ".cache"


class LLMProviderError(Exception):
    """Erreur remontee par un provider (modele indisponible, reponse pas du
    JSON valide malgre le mode JSON demande, timeout...). Volontairement une
    exception generique et non silencieuse - contrairement au reste de
    l'application principale (qui prefere souvent `None` a une exception
    pour ne jamais faire echouer un job planifie), ici une erreur DOIT
    remonter et arreter l'analyse plutot que de produire un rapport a
    moitie construit sur une reponse vide."""


@dataclass
class LLMResponse:
    """Enveloppe commune : la reponse parsee, plus des metadonnees utiles
    pour deboguer un rapport qu'on relit plusieurs jours plus tard (quel
    modele exactement, la reponse etait-elle en cache ou fraichement
    calculee, prompt exact envoye)."""

    data: dict[str, Any]
    model: str
    from_cache: bool
    raw_prompt: str = field(repr=False)
    raw_response_text: str = field(repr=False)


class LLMProvider(ABC):
    """Interface abstraite - un seul point d'entree (`complete`) pour que le
    reste de l'outil (analyst.py) ne sache jamais s'il parle a Ollama, a un
    autre backend local, ou au MockProvider de test."""

    @abstractmethod
    def _call_model(self, prompt: str, json_schema: dict | None) -> str:
        """Doit retourner la reponse BRUTE du modele (texte), sans parser le
        JSON - la validation/parsing est geree une fois pour toutes par
        `complete()` ci-dessous, commune a tous les providers."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...

    def complete(self, prompt: str, *, json_schema: dict | None = None, use_cache: bool = True) -> LLMResponse:
        cache_key = self._cache_key(prompt, json_schema)
        if use_cache:
            cached = _read_cache(cache_key)
            if cached is not None:
                logger.info("Cache LLM : hit (%s)", cache_key[:12])
                return LLMResponse(
                    data=cached["data"],
                    model=cached["model"],
                    from_cache=True,
                    raw_prompt=prompt,
                    raw_response_text=cached["raw_response_text"],
                )

        logger.info("Cache LLM : miss (%s) - appel du modele %s", cache_key[:12], self.model_name)
        raw_text = self._call_model(prompt, json_schema)
        data = _parse_json_response(raw_text)

        if use_cache:
            _write_cache(cache_key, {"data": data, "model": self.model_name, "raw_response_text": raw_text})

        return LLMResponse(data=data, model=self.model_name, from_cache=False, raw_prompt=prompt, raw_response_text=raw_text)

    def _cache_key(self, prompt: str, json_schema: dict | None) -> str:
        """Cle = hash(prompt + modele + schema) - le schema fait partie de la
        cle car un meme prompt avec un schema de sortie different doit
        produire une entree de cache distincte (voir docstring de module)."""
        payload = json.dumps(
            {"prompt": prompt, "model": self.model_name, "schema": json_schema},
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _parse_json_response(raw_text: str) -> dict:
    """Meme si on demande le mode JSON au modele, certains modeles Ollama
    entourent parfois leur reponse de texte libre ou de balises markdown
    (```json ... ```) - on essaie un parse direct, puis on retente en
    extrayant le premier bloc `{...}` trouve avant d'abandonner."""
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        pass

    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = raw_text[start : end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    raise LLMProviderError(
        f"Reponse du modele non parsable en JSON malgre le mode JSON demande "
        f"(premiers 200 caracteres : {raw_text[:200]!r})"
    )


def _read_cache(cache_key: str) -> dict | None:
    path = CACHE_DIR / f"{cache_key}.json"
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        logger.warning("Entree de cache LLM corrompue (%s) - ignoree, sera recalculee.", path)
        return None


def _write_cache(cache_key: str, payload: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{cache_key}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


class OllamaProvider(LLMProvider):
    """Implementation Ollama (https://ollama.com), 100% locale et gratuite -
    l'ecosysteme open source demande explicitement par l'utilisateur, en
    remplacement de toute API payante par abonnement.

    Prerequis (voir README.md) : Ollama installe et lance localement
    (`ollama serve`, generalement demarre automatiquement), et le modele
    choisi deja telecharge (`ollama pull <model>`). Aucune cle API, aucun
    compte, aucun abonnement.
    """

    def __init__(self, model: str = "llama3.1", base_url: str | None = None, timeout: float = 300.0):
        self._model = model
        self.base_url = (base_url or os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434").rstrip("/")
        self.timeout = timeout

    @property
    def model_name(self) -> str:
        return self._model

    def _call_model(self, prompt: str, json_schema: dict | None) -> str:
        import httpx

        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0},
        }
        # Mode JSON natif d'Ollama (voir https://github.com/ollama/ollama/
        # blob/main/docs/api.md#json-mode) : le champ "format" accepte soit
        # la chaine "json" (JSON generique), soit un JSON Schema complet pour
        # contraindre la structure exacte - on utilise le schema quand il est
        # fourni, sinon on retombe sur le mode JSON generique.
        payload["format"] = json_schema if json_schema else "json"

        try:
            response = httpx.post(f"{self.base_url}/api/generate", json=payload, timeout=self.timeout)
            response.raise_for_status()
        except httpx.ConnectError as exc:
            raise LLMProviderError(
                f"Impossible de joindre Ollama sur {self.base_url} - est-il bien lance ? "
                f"(voir README.md : `ollama serve`, puis `ollama pull {self._model}`)"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise LLMProviderError(
                f"Ollama a repondu une erreur HTTP {exc.response.status_code} - le modele "
                f"'{self._model}' est-il telecharge ? (`ollama pull {self._model}`)"
            ) from exc

        body = response.json()
        return body.get("response", "")


class MockProvider(LLMProvider):
    """Provider factice, sans aucun appel reseau - sert a tester tout le
    reste du pipeline (analyst.py : construction du prompt, validation des
    citations, rendu du rapport) sans avoir Ollama installe/lance. Retourne
    toujours la meme reponse fournie a la construction, ignore le cache par
    defaut (use_cache=False cote appelant recommande en test) pour rester
    previsible d'un test a l'autre."""

    def __init__(self, canned_response: dict, model: str = "mock-model"):
        self.canned_response = canned_response
        self._model = model
        self.calls: list[str] = []

    @property
    def model_name(self) -> str:
        return self._model

    def _call_model(self, prompt: str, json_schema: dict | None) -> str:
        self.calls.append(prompt)
        return json.dumps(self.canned_response, ensure_ascii=False)
