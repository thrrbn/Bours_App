"""Exceptions metier communes, partagees par tous les domaines, et leurs handlers FastAPI."""
from fastapi import Request
from fastapi.responses import JSONResponse


class AssetNotFoundError(Exception):
    def __init__(self, identifier: str):
        self.identifier = identifier
        super().__init__(f"Actif introuvable: {identifier}")


class DataProviderError(Exception):
    """Levee quand un fournisseur externe (Yahoo Finance, RSS...) echoue."""


class InsufficientDataError(Exception):
    """Levee quand il n'y a pas assez de donnees pour calculer un signal fiable."""


async def asset_not_found_handler(request: Request, exc: AssetNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


async def data_provider_error_handler(request: Request, exc: DataProviderError) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": str(exc)})


async def insufficient_data_handler(request: Request, exc: InsufficientDataError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


def register_exception_handlers(app) -> None:
    app.add_exception_handler(AssetNotFoundError, asset_not_found_handler)
    app.add_exception_handler(DataProviderError, data_provider_error_handler)
    app.add_exception_handler(InsufficientDataError, insufficient_data_handler)
