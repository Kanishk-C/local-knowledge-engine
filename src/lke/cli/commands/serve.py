"""CLI command to run the REST API server."""

import logging
import typer
import uvicorn

from lke.cli.container import container, initialize_container


logger = logging.getLogger(__name__)

app = typer.Typer(name="serve", help="Start the REST API server.")

@app.callback(invoke_without_command=True)
def serve() -> None:
    """Start the REST API server."""
    initialize_container()
    
    from lke.config.models import ApplicationConfig
    config = container.resolve(ApplicationConfig)
    
    # We must explicitly read host and port from config
    host = config.api.host
    port = config.api.port
    
    # Strictly enforce localhost binding for safety, unless configured explicitly otherwise,
    # but the default config forces 127.0.0.1. Let's add a loud warning if it's not localhost.
    if host not in ("127.0.0.1", "localhost", "::1"):
        logger.warning(
            f"SECURITY WARNING: Server is configured to bind to {host}. "
            f"This is a local-only tool with no authentication. Exposing it to a network is highly dangerous."
        )
    else:
        logger.info(f"Starting API server on http://{host}:{port}")

    # Launch uvicorn
    # uvicorn.run requires an import string if reload=True, but we'll run it directly
    uvicorn.run(
        "lke.api.app:create_app",
        host=host,
        port=port,
        factory=True,
        log_level="info",
    )
