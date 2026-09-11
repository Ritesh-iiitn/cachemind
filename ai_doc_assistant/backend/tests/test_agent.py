import pytest
from backend.app.models.schemas import QueryRequest, DocumentChunk
from backend.app.agents.planner import CacheAwarePlanner
from backend.app.agents.verifier import AnswerVerifier

def test_planner_complexity_routing():
    planner = CacheAwarePlanner()
    
    req1 = QueryRequest(kb_id="kb_1", query="What is vector search?")
    plan1 = planner.create_plan(req1, kb_version=1)
    assert plan1.query_complexity == "simple"
    assert plan1.model_tier == "small"
    
    req2 = QueryRequest(kb_id="kb_1", query="Compare the scalability tradeoffs and retrieval performance of BM25 vs FAISS.")
    plan2 = planner.create_plan(req2, kb_version=1)
    assert plan2.query_complexity == "multi_hop"
    assert plan2.retrieval_strategy == "hybrid"
    assert plan2.model_tier == "large"
    assert plan2.verification_required is True

def test_answer_verifier():
    verifier = AnswerVerifier()
    chunks = [
        DocumentChunk(
            id="chk_1", document_id="doc_1", kb_id="kb_1", document_version=1,
            chunk_index=0, page_number=1, text="Prefix caching allows prompt KV tensor reuse.", token_count=10
        )
    ]
    
    valid, reason, citations = verifier.verify("What is prefix caching?", "Prefix caching allows prompt KV tensor reuse across multiple requests.", chunks)
    assert valid is True
    assert len(citations) >= 1
    
    invalid, reason2, _ = verifier.verify("What is solar energy?", "The sun produces thermonuclear fusion.", chunks)
    assert invalid is False
