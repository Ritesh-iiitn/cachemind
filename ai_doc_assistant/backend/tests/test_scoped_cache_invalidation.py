import pytest
from backend.app.cache.exact_cache import exact_cache
from backend.app.cache.semantic_cache import semantic_cache
from backend.app.cache.retrieval_cache import retrieval_cache
from backend.app.cache.invalidation import invalidator


def test_scoped_cache_invalidation_preserves_unrelated_kbs():
    kb_a = "kb_tenant_alpha"
    kb_b = "kb_tenant_beta"

    # Seed Exact Cache
    exact_cache.put(kb_id=kb_a, kb_version=1, query="What is Paxos?", value={"kb_id": kb_a, "answer": "Paxos is a consensus protocol"})
    exact_cache.put(kb_id=kb_b, kb_version=1, query="What is Raft?", value={"kb_id": kb_b, "answer": "Raft is a consensus protocol"})


    # Verify both exist
    assert exact_cache.get(kb_id=kb_a, kb_version=1, query="What is Paxos?") is not None
    assert exact_cache.get(kb_id=kb_b, kb_version=1, query="What is Raft?") is not None

    # Perform scoped invalidation for kb_a ONLY
    result = invalidator.invalidate_knowledge_base(
        kb_id=kb_a,
        tenant_id="tenant_1",
        document_id="doc_1",
        kb_version=2
    )

    assert result["kb_id"] == kb_a
    assert result["status"] == "invalidated"
    assert result["exact_cache_purged"] >= 1

    # Verify kb_a is purged but kb_b is PRESERVED
    assert exact_cache.get(kb_id=kb_a, kb_version=1, query="What is Paxos?") is None
    cached_b = exact_cache.get(kb_id=kb_b, kb_version=1, query="What is Raft?")
    assert cached_b is not None
    assert cached_b["answer"] == "Raft is a consensus protocol"
