import pytest
from lke.application.services.eval_service import EvalService, EvalQueryContext

def test_eval_service_perfect_match():
    service = EvalService()
    context = EvalQueryContext(
        query="test",
        expected_documents={"doc1.md", "doc2.md"},
        retrieved_documents=["doc1.md", "doc2.md"],
        expected_contains=[],
        expected_excludes=[]
    )
    result = service.calculate_metrics(context, k=2)
    assert result.precision == 1.0
    assert result.recall == 1.0
    assert result.mrr == 1.0

def test_eval_service_partial_match():
    service = EvalService()
    context = EvalQueryContext(
        query="test",
        expected_documents={"doc1.md", "doc2.md"},
        retrieved_documents=["doc3.md", "doc1.md"],
        expected_contains=[],
        expected_excludes=[]
    )
    result = service.calculate_metrics(context, k=2)
    assert result.precision == 0.5
    assert result.recall == 0.5
    assert result.mrr == 0.5  # doc1 is at rank 2

def test_eval_service_no_match():
    service = EvalService()
    context = EvalQueryContext(
        query="test",
        expected_documents={"doc1.md"},
        retrieved_documents=["doc2.md"],
        expected_contains=[],
        expected_excludes=[]
    )
    result = service.calculate_metrics(context, k=1)
    assert result.precision == 0.0
    assert result.recall == 0.0
    assert result.mrr == 0.0

def test_eval_service_duplicates_handled():
    service = EvalService()
    context = EvalQueryContext(
        query="test",
        expected_documents={"doc1.md"},
        retrieved_documents=["doc1.md", "doc1.md"],
        expected_contains=[],
        expected_excludes=[]
    )
    result = service.calculate_metrics(context, k=2)
    # The unique retrieved is just ['doc1.md']
    assert result.precision == 1.0
    assert result.recall == 1.0
    assert result.mrr == 1.0

def test_aggregate_results():
    service = EvalService()
    ctx1 = EvalQueryContext("test1", {"doc1.md"}, ["doc1.md"], [], [])
    ctx2 = EvalQueryContext("test2", {"doc2.md"}, ["doc3.md"], [], [])
    
    r1 = service.calculate_metrics(ctx1, k=1) # p=1, r=1, mrr=1
    r2 = service.calculate_metrics(ctx2, k=1) # p=0, r=0, mrr=0
    
    agg = service.aggregate_results([r1, r2])
    assert agg.mean_precision == 0.5
    assert agg.mean_recall == 0.5
    assert agg.mrr == 0.5
