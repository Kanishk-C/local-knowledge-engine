"""Init command for verifying and bootstrapping the LKE environment."""

import typer
from rich.panel import Panel

from lke.cli.console import console
from lke.cli.container import container
from lke.cli.formatting import print_error, print_success
from lke.config.models import ApplicationConfig
from lke.domain.protocols.embedding_provider import EmbeddingProvider
from lke.domain.repositories.vector_repository import VectorRepository

app = typer.Typer(name="init", help="Initialize and validate the LKE environment.")


@app.callback(invoke_without_command=True)
def init_command() -> None:
    """Validate the runtime environment and check dependencies."""

    with console.status("[info]Validating LKE environment...[/info]") as status:
        # Check Configuration
        status.update("[info]Checking Configuration...[/info]")
        config = container.resolve(ApplicationConfig)
        print_success("Configuration")

        # Check AI Provider (Ollama & Embedding Model)
        status.update("[info]Checking AI Provider (Ollama)...[/info]")
        provider = container.resolve(EmbeddingProvider)
        provider_health = provider.health_check()
        if provider_health.healthy:
            print_success("Ollama")
            print_success(f"Embedding Model ({config.embeddings.model_name})")
        else:
            print_error("Ollama")
            console.print(f"[secondary]  Reason: {provider_health.message}[/secondary]")
            print_error("Embedding Model")
            raise typer.Exit(code=3)

        # Check Vector Repository (LanceDB & Schema & Storage)
        status.update("[info]Checking Vector Repository (LanceDB)...[/info]")
        repo = container.resolve(VectorRepository)
        repo_health = repo.health()
        if not repo_health.healthy:
            try:
                repo.initialize()
                repo_health = repo.health()
            except Exception:
                pass

        if repo_health.healthy:
            print_success("LanceDB")
            print_success("Repository Schema")
            print_success(f"Storage ({config.paths.vector_db})")
        else:
            print_error("LanceDB")
            console.print(f"[secondary]  Reason: {repo_health.message}[/secondary]")
            print_error("Repository Schema")
            print_error("Storage")
            raise typer.Exit(code=2)

    console.print()
    console.print(
        Panel(
            "[success]LKE is initialized and ready![/success]",
            border_style="success",
            expand=False,
        )
    )
