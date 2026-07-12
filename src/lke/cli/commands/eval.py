"""Command to evaluate the search system."""

import sys
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console
from rich.table import Table
from rich.text import Text

from lke.application.services.eval_service import EvalQueryContext, EvalService
from lke.application.services.indexing_pipeline import IndexingPipeline
from lke.application.services.search_service import SearchService
from lke.cli.formatting import print_error, print_info, print_success, print_warning
from lke.config.models import ApplicationConfig

app = typer.Typer(name="eval", help="Evaluate search and retrieval quality.")

console = Console()

@app.callback(invoke_without_command=True)
def run_eval(
    ctx: typer.Context,
    dataset: Path = typer.Option(
        None,
        "--dataset", "-d",
        help="Path to evaluation dataset YAML (defaults based on mode)"
    ),
    corpus: Path = typer.Option(
        Path("tests/eval/corpus"),
        "--corpus", "-c",
        help="Path to evaluation corpus directory"
    ),
    threshold: float = typer.Option(
        0.5,
        "--threshold", "-t",
        help="Minimum required Mean Recall@K for the evaluation to pass"
    ),
    mode: str = typer.Option(
        "search",
        "--mode", "-m",
        help="Evaluation mode: 'search' or 'related-notes'"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Print detailed results per query"
    )
):
    """Run evaluation suite against the vector search engine or enrichment pipeline."""
    if ctx.invoked_subcommand is not None:
        return
        
    import tempfile
    
    if dataset is None:
        if mode == "related-notes":
            dataset = Path("tests/eval/related_notes_dataset.yaml")
        else:
            dataset = Path("tests/eval/dataset.yaml")
    
    if not dataset.exists():
        print_error(f"Evaluation dataset not found at {dataset}")
        sys.exit(1)
        
    if not corpus.exists():
        print_error(f"Evaluation corpus not found at {corpus}")
        sys.exit(1)
        
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        print_info(f"Using isolated evaluation environment at {temp_path}")
        
        from lke.config.loader import load_configuration
        from lke.infrastructure.providers.ollama_provider import OllamaProvider
        from lke.infrastructure.repositories.lancedb_repository import LanceDBRepository
        from lke.infrastructure.parsing.markdown_parser import MarkdownParser
        from lke.domain.services.chunking import ChunkingService
        from lke.domain.services.embedding import EmbeddingService
        from lke.domain.services.relevance import RelevanceScorer
        from lke.application.services.indexing_pipeline import IndexingPipeline, _MetadataStore
        from lke.application.services.search_service import SearchService
        
        eval_config = load_configuration()
        eval_config.paths.vector_db = temp_path / "vectors.lance"
        eval_config.paths.metadata_file = temp_path / "metadata.json"
        eval_config.search.min_similarity = 0.0
        
        provider = OllamaProvider(eval_config.ai_provider, eval_config.embeddings, eval_config.enrichment)
        vector_repo = LanceDBRepository(eval_config.paths, eval_config.embeddings)
        parser = MarkdownParser()
        metadata_store = _MetadataStore(eval_config.paths.metadata_file)
        chunking_service = ChunkingService(
            max_tokens=eval_config.embeddings.chunk_size,
            overlap_tokens=eval_config.embeddings.chunk_overlap,
            min_tokens=eval_config.embeddings.min_chunk_size,
        )
        embedding_service = EmbeddingService(provider, eval_config.embeddings)
        
        vector_repo.initialize()
        
        indexing_pipeline = IndexingPipeline(
            parser, chunking_service, embedding_service, vector_repo, metadata_store
        )
        
        relevance_scorer = RelevanceScorer(min_similarity=0.0)
        search_service = SearchService(provider, vector_repo, relevance_scorer, eval_config.search)
        eval_service = EvalService()
        
        print_info(f"Indexing evaluation corpus at {corpus}...")
        result = indexing_pipeline.index_vault(corpus)
        if result.failed_documents > 0:
            print_error("Failed to index evaluation corpus.")
            sys.exit(1)
            
        print_success(f"Indexed {result.successful_documents} files successfully in isolated DB.")
        
        with open(dataset, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            
        if mode == "related-notes":
            run_related_notes_eval(data, corpus, eval_config, vector_repo)
        else:
            run_search_eval(data, eval_config, search_service, eval_service, threshold, verbose)

def run_related_notes_eval(data, corpus: Path, eval_config, vector_repo):
    from lke.application.services.enrichment_pipeline import EnrichmentPipeline
    from lke.infrastructure.parsing.markdown_writer import MarkdownFrontmatterWriter
    from lke.domain.protocols.vocabulary import TagVocabulary, FolderVocabulary
    
    pairs = data.get("pairs", [])
    if not pairs:
        print_warning("No pairs found in dataset.")
        sys.exit(0)
        
    print_info(f"Running related-notes sweep on {len(pairs)} labeled pairs...")
    
    class DummyVocab:
        def get_all(self): return []
        def add(self, *args): pass
        
    class DummyAI:
        def generate(self, *args, **kwargs): return {}
        
    class DummyWriter:
        def write_enrichment(self, *args, **kwargs): return ""
        def move_file(self, *args, **kwargs): return ""

    from lke.infrastructure.parsing.markdown_parser import MarkdownParser
    from lke.application.services.indexing_pipeline import _MetadataStore
    
    # We only need _find_related_notes, so dummies are fine for the rest
    pipeline = EnrichmentPipeline(
        parser=MarkdownParser(),
        ai_provider=DummyAI(),
        vector_repo=vector_repo,
        tag_vocab=DummyVocab(),
        folder_vocab=DummyVocab(),
        writer=DummyWriter(),
        metadata_store=_MetadataStore(eval_config.paths.metadata_file),
        config=eval_config.enrichment
    )
    
    # Pre-resolve real absolute paths for documents
    doc_paths = {}
    for p in corpus.rglob("*.md"):
        doc_paths[p.name] = str(p.absolute())

    thresholds = [x / 100.0 for x in range(40, 85, 5)]
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Threshold")
    table.add_column("True Positives", justify="center")
    table.add_column("False Positives", justify="center")
    table.add_column("True Negatives", justify="center")
    table.add_column("False Negatives", justify="center")
    
    for t in thresholds:
        pipeline._config.related_notes_threshold = t
        tp, fp, tn, fn = 0, 0, 0, 0
        
        for pair in pairs:
            name_a = pair["note_a"]
            name_b = pair["note_b"]
            is_related = pair["is_related"]
            
            doc_a = doc_paths.get(name_a)
            doc_b = doc_paths.get(name_b)
            
            if not doc_a or not doc_b:
                continue
                
            # Related notes is unidirectional in its search query, but we only need to check if one hits the other
            related_to_a = pipeline._find_related_notes(doc_a)
            linked = any(name_b.replace(".md", "") in link for link in related_to_a)
            
            if is_related:
                if linked: tp += 1
                else: fn += 1
            else:
                if linked: fp += 1
                else: tn += 1
                
        table.add_row(f"{t:.2f}", str(tp), str(fp), str(tn), str(fn))
        
    console.print(table)
    
def run_search_eval(data, eval_config, search_service, eval_service, threshold, verbose):
    evaluations = data.get("evaluations", [])
    if not evaluations:
        print_warning("No evaluations found in dataset.")
        sys.exit(0)
        
    print_info(f"Running {len(evaluations)} evaluation queries...")
    
    query_results = []
    
    for eval_item in evaluations:
        query_text = eval_item["query"]
        expected_docs = set(eval_item.get("expected_relevant_documents", []))
        expected_contains = eval_item.get("expected_answer_contains", [])
        expected_excludes = eval_item.get("expected_answer_excludes", [])
        
        top_k = eval_config.search.top_k
        search_results = search_service.search(query_text, top_k=top_k)
        
        retrieved_basenames = [Path(r.document_id).name for r in search_results]
        
        context = EvalQueryContext(
            query=query_text,
            expected_documents=expected_docs,
            retrieved_documents=retrieved_basenames,
            expected_contains=expected_contains,
            expected_excludes=expected_excludes
        )
        
        q_result = eval_service.calculate_metrics(context, k=top_k)
        query_results.append(q_result)
        
        if verbose:
            console.print(f"\n[bold blue]Query:[/bold blue] {query_text}")
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Rank")
            table.add_column("Retrieved Document")
            table.add_column("Match?", justify="center")
            
            for i, retrieved_doc in enumerate(q_result.retrieved):
                match_text = "[green]YES[/green]" if retrieved_doc in expected_docs else "[red]NO[/red]"
                table.add_row(str(i+1), retrieved_doc, match_text)
                
            console.print(table)
            
            missed = expected_docs - set(q_result.retrieved)
            if missed:
                console.print(f"[yellow]Missed:[/yellow] {', '.join(missed)}")
            
            console.print(f"[dim]P@{top_k}: {q_result.precision:.2f} | R@{top_k}: {q_result.recall:.2f} | MRR: {q_result.mrr:.2f}[/dim]")

    aggregate = eval_service.aggregate_results(query_results)
    
    console.print("\n[bold]Aggregate Results[/bold]")
    console.print(f"Mean Precision@{eval_config.search.top_k}: {aggregate.mean_precision:.3f}")
    console.print(f"Mean Recall@{eval_config.search.top_k}:    {aggregate.mean_recall:.3f}")
    console.print(f"Mean Reciprocal Rank: {aggregate.mrr:.3f}")
    
    if aggregate.mean_recall < threshold:
        print_error(f"Evaluation failed. Mean Recall ({aggregate.mean_recall:.3f}) is below threshold ({threshold}).")
        sys.exit(1)
    else:
        print_success(f"Evaluation passed. Mean Recall ({aggregate.mean_recall:.3f}) meets or exceeds threshold ({threshold}).")
        
if __name__ == "__main__":
    app()
