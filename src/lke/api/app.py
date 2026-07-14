"""FastAPI application factory."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lke.api.errors import setup_exception_handlers
from lke.api.routers import search, ask
from lke.cli.container import initialize_container


logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    # Ensure DI container is initialized (this parses config and sets up logging)
    initialize_container()
    
    app = FastAPI(
        title="Local Knowledge Engine API",
        description="REST API for the Local Knowledge Engine",
        version="0.1.0",
    )
    
    # We only allow local requests, but for local web UIs, CORS might be needed.
    # Restrict completely to localhost for safety.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost", "http://127.0.0.1"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Register error handlers
    setup_exception_handlers(app)
    
    # Include routers
    app.include_router(search.router, prefix="/api", tags=["search"])
    app.include_router(ask.router, prefix="/api", tags=["ask"])
    
    return app
