import pytest
import numpy as np
from backend.app.cache.exact_cache import ExactResponseCache
from backend.app.cache.semantic_cache import SemanticResponseCache
from backend.app.cache.retrieval_cache import RetrievalResultCache
from backend.app.cache.prefix_cache import PrefixPromptCache
from backend.app.models.schemas import DocumentChunk

def test_exact_cache_normalization_and_hit():
    cache = ExactResponseCache(max_entries=100)
    data = {"answer": "Agentic RAG uses feedback loops.", "model_used": "qwen2.5:3b"}
    
    # Store with extra spaces and punctuation
    cache.put("kb_1", 1, "  What is Agentic RAG?  ", data)
    
    # Retrieve with lowercase and different spacing
    hit = cache.get("kb_1", 1, "what is agentic rag")
    assert hit is not None
    assert hit["answer"] == data["answer"]
    
    # Version mismatch should MISS
    miss_ver = cache.get("kb_1", 2, "what is agentic rag")
    assert miss_ver is None

def test_semantic_cache_similarity_and_guardrail():
    cache = SemanticResponseCache(similarity_threshold=0.85)
    
    # Mock orthogonal vectors
    vec1 = np.array([1.0, 0.0, 0.0] + [0.0] * 381, dtype="float32")
    vec1 = vec1 / np.linalg.norm(vec1)
    
    vec2 = np.array([0.95, 0.05, 0.0] + [0.0] * 381, dtype="float32")
    vec2 = vec2 / np.linalg.norm(vec2)
    
    data = {"answer": "L1 cache is exact matching.", "execution_plan": {"plan_id": "test", "reason": "", "query_complexity": "simple", "retrieval_strategy": "none", "use_reranker": False, "model_tier": "small", "model_name": "qwen", "verification_required": False, "estimated_latency_ms": 10.0}}
    cache.put("kb_1", 1, "Explain L1 exact caching mechanism", data, query_vec=vec1)
    
    # Test high similarity lookup with overlapping entities
    hit_data, score = cache.lookup("kb_1", 1, "Explain L1 exact caching mechanism details", query_vec=vec2)
    assert hit_data is not None
    assert score >= 0.85

def test_retrieval_cache_and_invalidation():
    cache = RetrievalResultCache(max_entries=50)
    dummy_chunk = DocumentChunk(
        id="c1", document_id="d1", kb_id="kb_1", document_version=1,
        chunk_index=0, page_number=1, text="Distributed KV cache architecture.", token_count=10
    )
    
    cache.put("kb_1", 1, "hybrid", 5, "What is KV cache?", [dummy_chunk])
    
    retrieved = cache.get("kb_1", 1, "hybrid", 5, "What is KV cache?")
    assert retrieved is not None
    assert len(retrieved) == 1
    assert retrieved[0].id == "c1"
    
    # Invalidation
    purged = cache.invalidate_kb("kb_1")
    assert purged >= 1
    assert cache.get("kb_1", 1, "hybrid", 5, "What is KV cache?") is None

def test_prefix_cache_savings():
    pcache = PrefixPromptCache(min_prefix_tokens=10)
    system_prompt = "You are CacheMind, an adaptive agentic RAG system that optimizes latency and cost."
    
    res1 = pcache.register_or_check_prefix(system_prompt, model="qwen2.5:3b")
    assert res1["hit"] is False
    
    res2 = pcache.register_or_check_prefix(system_prompt, model="qwen2.5:3b")
    assert res2["hit"] is True
    assert res2["tokens_saved"] > 0
