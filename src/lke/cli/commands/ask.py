"""Command to ask questions over the local knowledge engine."""

import typer
from rich.console import Console
from rich.markdown import Markdown

from lke.cli.formatting import print_error, print_warning
from lke.domain.exceptions import DomainError
from lke.cli.container import container
from lke.application.services.rag_service import RAGService

app = typer.Typer(name="ask", help="Ask a question and get a synthesized answer based on your vault.")

console = Console()

@app.callback(invoke_without_command=True)
def ask(
    query: str = typer.Argument(
        ...,
        help="The natural language question to ask."
    )
):
    """Ask a question to the RAG pipeline."""
    try:
        rag_service: RAGService = container.resolve(RAGService)
    except Exception as e:
        print_error(f"Failed to initialize RAG Service: {e}")
        raise typer.Exit(1)
        
    try:
        response = rag_service.ask(query)
    except DomainError as e:
        print_error(str(e))
        raise typer.Exit(1)
    except Exception as e:
        print_error(f"An unexpected error occurred: {e}")
        raise typer.Exit(1)
        
    console.print("\n")
    console.print(Markdown(response.answer))
    console.print("\n")
    
    if response.sources:
        console.print("[dim]Sources:[/dim]")
        # Keep track of printed documents to avoid duplicate entries for the same file
        printed_docs = set()
        for i, hit in enumerate(response.sources, 1):
            doc_id = hit.document_id
            if doc_id not in printed_docs:
                title = hit.metadata.get('title') or doc_id
                console.print(f"[dim]{i}. {title}[/dim]")
                printed_docs.add(doc_id)
    else:
        print_warning("No sources were found to answer this question.")
        
if __name__ == "__main__":
    app()
