"""Search command for querying the indexed knowledge vault."""

import typer
from rich.panel import Panel

from lke.application.services.search_service import SearchService
from lke.cli.console import console
from lke.cli.container import container
from lke.cli.formatting import format_search_result

app = typer.Typer(name="search", help="Search indexed documents using semantic similarity.")


@app.callback(invoke_without_command=True)
def search_command(
    query: str = typer.Argument(..., help="The semantic search query."),
    top_k: int = typer.Option(5, "--top-k", help="Number of results to return."),
) -> None:
    """Search indexed documents using semantic similarity."""

    with console.status(f"[info]Searching for '{query}'...[/info]"):
        search_service = container.resolve(SearchService)
        try:
            results = search_service.search(query=query, top_k=top_k)
        except Exception as e:
            console.print("[error]✗ Search Failed[/error]")
            console.print(f"[secondary]{str(e)}[/secondary]")
            raise typer.Exit(code=4) from e

    if not results:
        console.print(
            Panel(
                "[warning]No matching documents were found.[/warning]\n\n"
                "[secondary]Suggestions:[/secondary]\n"
                "• Increase --top-k\n"
                "• Lower the similarity threshold\n"
                "• Index additional documents",
                border_style="warning",
                expand=False,
            )
        )
        return

    # Render results
    for result in results:
        console.print(format_search_result(result))
