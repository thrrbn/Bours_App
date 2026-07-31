"""Exceptions metier communes, partagees par tous les domaines, et leurs handlers FastAPI."""
from fastapi import Request
from fastapi.responses import JSONResponse


class AssetNotFoundError(Exception):
    def __init__(self, identifier: str):
        self.identifier = identifier
        super().__init__(f"Actif introuvable: {identifier}")


class NotFoundError(Exception):
    """404 generique pour une ressource autre qu'un Asset (ex. un mot-cle
    personnalise, voir news/service.py::delete_custom_keyword) - AssetNotFoundError
    reste reserve aux actifs pour ne pas afficher un message trompeur
    ("Actif introuvable") sur une ressource qui n'en est pas un."""

    def __init__(self, resource: str, identifier: str):
        self.resource = resource
        self.identifier = identifier
        super().__init__(f"{resource} introuvable: {identifier}")


class DataProviderError(Exception):
    """Levee quand un fournisseur externe (Yahoo Finance, RSS...) echoue."""


class ConflictError(Exception):
    """409 - action refusee a cause d'un etat existant incompatible (ex.
    suppression d'un actif encore detenu en portefeuille, voir
    assets/service.py::delete_asset)."""


class InsufficientDataError(Exception):
    """Levee quand il n'y a pas assez de donnees pour calculer un signal fiable."""


async def asset_not_found_handler(request: Request, exc: AssetNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


async def data_provider_error_handler(request: Request, exc: DataProviderError) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": str(exc)})


async def conflict_error_handler(request: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


async def insufficient_data_handler(request: Request, exc: InsufficientDataError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


def register_exception_handlers(app) -> None:
    app.add_exception_handler(AssetNotFoundError, asset_not_found_handler)
    app.add_exception_handler(NotFoundError, not_found_handler)
    app.add_exception_handler(ConflictError, conflict_error_handler)
    app.add_exception_handler(DataProviderError, data_provider_error_handler)
    app.add_exception_handler(InsufficientDataError, insufficient_data_handler)
