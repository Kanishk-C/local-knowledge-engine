"""Application service for running evaluations."""

from dataclasses import dataclass
from typing import Any

from lke.domain.models.search import SearchResult


@dataclass
class EvalQueryContext:
    """Context for a single evaluation query."""
    query: str
    expected_documents: set[str]
    retrieved_documents: list[str]  # Ordered list of document IDs
    expected_contains: list[str]
    expected_excludes: list[str]


@dataclass
class EvalQueryResult:
    """Result of evaluating a single query."""
    query: str
    precision: float
    recall: float
    mrr: float
    retrieved: list[str]
    expected: set[str]


@dataclass
class EvalAggregateResult:
    """Aggregate results across an evaluation suite."""
    mean_precision: float
    mean_recall: float
    mrr: float
    query_results: list[EvalQueryResult]


class EvalService:
    """Service for calculating IR evaluation metrics."""

    def calculate_metrics(self, context: EvalQueryContext, k: int) -> EvalQueryResult:
        """Calculate Precision@k, Recall@k, and MRR for a single query.
        
        Args:
            context: The evaluation context for the query.
            k: The maximum number of retrieved documents to consider (top_k).
            
        Returns:
            An EvalQueryResult containing the calculated metrics.
        """
        # Consider only the top_k retrieved documents, but we deduplicate
        # because the same document might have multiple chunks returned.
        # We preserve order for MRR.
        seen = set()
        unique_retrieved = []
        for doc in context.retrieved_documents:
            if doc not in seen:
                seen.add(doc)
                unique_retrieved.append(doc)
                
        top_k_retrieved = unique_retrieved[:k]
        
        retrieved_set = set(top_k_retrieved)
        expected_set = context.expected_documents
        
        # True positives in top_k
        tp = len(retrieved_set.intersection(expected_set))
        
        precision = tp / len(top_k_retrieved) if top_k_retrieved else 0.0
        recall = tp / len(expected_set) if expected_set else 1.0
        
        mrr = 0.0
        for i, doc in enumerate(top_k_retrieved):
            if doc in expected_set:
                mrr = 1.0 / (i + 1)
                break
                
        return EvalQueryResult(
            query=context.query,
            precision=precision,
            recall=recall,
            mrr=mrr,
            retrieved=top_k_retrieved,
            expected=expected_set,
        )

    def aggregate_results(self, results: list[EvalQueryResult]) -> EvalAggregateResult:
        """Calculate mean metrics across all query results."""
        if not results:
            return EvalAggregateResult(0.0, 0.0, 0.0, [])
            
        mean_precision = sum(r.precision for r in results) / len(results)
        mean_recall = sum(r.recall for r in results) / len(results)
        mrr = sum(r.mrr for r in results) / len(results)
        
        return EvalAggregateResult(
            mean_precision=mean_precision,
            mean_recall=mean_recall,
            mrr=mrr,
            query_results=results,
        )
