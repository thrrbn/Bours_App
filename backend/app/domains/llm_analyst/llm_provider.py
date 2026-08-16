"""
Interface LLM abstraite + implementation Ollama - adaptation directe de
`tools/backtest_analyst/llm_provider.py` (14/08/2026, Chantier 0) pour
l'instance locale integree (16/08/2026, voir docs/20-instance-locale-pc-mac.md).

Ce module vit dans `backend/app` mais n'est JAMAIS execute sur le NAS en
pratique : `router.py::require_enabled` bloque tout appel tant que
`settings.enable_llm_analyst` n'est pas explicitement mis a true (jamais le
cas dans le docker-compose.yml deploye sur le NAS). La seule difference
reelle avec la version `tools/` : les defauts de modele/URL viennent de
`app.config.get_settings()` (coherent avec le reste du backend, qui ne lit
jamais `os.environ` directement) plutot que d'un argument CLI.

Sans cache, aucune analyse impliquant un LLM n'est reproductible ni
economiquement viable (chaque re-execution recalculerait tout) - le cache
disque ci-dessous est une partie integrante de l'abstraction, pas une
optimisation secondaire (meme raisonnement que la version `tools/`).
"""
from __future__ import annotations

import hashlib
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)

# Sous backend/.cache/llm_analyst/ - jamais versionne (voir .gitignore),
# distinct du cache de tools/backtest_analyst/.cache/ (deux processus/deux
# usages differents, pas de raison de les partager).
CACHE_DIR = Path(__file__).resolve().parent.parent.parent.parent / ".cache" / "llm_analyst"


class LLMProviderError(Exception):
    """Erreur remontee par un provider (modele indisponible, reponse pas du
    JSON valide malgre le mode JSON demande, timeout...). Volontairement une
    exception qui remonte et arrete l'analyse plutot que de produire un
    rapport a moitie construit sur une reponse vide - voir
    jobs/llm_analysis_job.py qui la capture pour marquer le job 'failed'."""


@dataclass
class LLMResponse:
    """Enveloppe commune : la reponse parsee, plus des metadonnees utiles
    pour deboguer un rapport relu plusieurs jours plus tard (quel modele
    exactement, la reponse etait-elle en cache, prompt exact envoye)."""

    data: dict[str, Any]
    model: str
    from_cache: bool
    raw_prompt: str = field(repr=False)
    raw_response_text: str = field(repr=False)


class LLMProvider(ABC):
    """Interface abstraite - un seul point d'entree (`complete`) pour que le
    reste du domaine (analyst.py) ne sache jamais s'il parle a Ollama ou au
    MockProvider de test."""

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
    """Implementation Ollama (https://ollama.com), 100% locale et gratuite.

    Prerequis : Ollama installe et lance localement (`ollama serve`,
    generalement demarre automatiquement), et le modele choisi deja
    telecharge (`ollama pull <model>`). Aucune cle API, aucun compte, aucun
    abonnement - voir docs/20-instance-locale-pc-mac.md."""

    def __init__(self, model: str | None = None, base_url: str | None = None, timeout: float = 300.0):
        settings = get_settings()
        self._model = model or settings.ollama_model
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
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
        # Mode JSON natif d'Ollama : le champ "format" accepte soit la
        # chaine "json" (JSON generique), soit un JSON Schema complet pour
        # contraindre la structure exacte.
        payload["format"] = json_schema if json_schema else "json"

        try:
            response = httpx.post(f"{self.base_url}/api/generate", json=payload, timeout=self.timeout)
            response.raise_for_status()
        except httpx.ConnectError as exc:
            raise LLMProviderError(
                f"Impossible de joindre Ollama sur {self.base_url} - est-il bien lance ? "
                f"(`ollama serve`, puis `ollama pull {self._model}`) - voir docs/20-instance-locale-pc-mac.md."
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
    reste du domaine (analyst.py : construction du prompt, validation des
    citations, rendu du rapport) sans avoir Ollama installe/lance."""

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
