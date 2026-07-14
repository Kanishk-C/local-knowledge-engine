"""Error handling for the FastAPI application."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from lke.domain.exceptions import (
    DomainError,
    InfrastructureError,
    LKEError,
)


def setup_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers on the FastAPI app."""

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"error": "Bad Request", "details": str(exc)},
        )

    @app.exception_handler(InfrastructureError)
    async def infrastructure_error_handler(request: Request, exc: InfrastructureError) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"error": "Service Unavailable", "details": str(exc)},
        )

    @app.exception_handler(LKEError)
    async def lke_base_error_handler(request: Request, exc: LKEError) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"error": "An internal error occurred.", "details": str(exc)},
        )

