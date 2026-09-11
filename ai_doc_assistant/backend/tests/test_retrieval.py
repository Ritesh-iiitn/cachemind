import pytest
from backend.app.models.schemas import DocumentChunk
from backend.app.retrieval.bm25 import BM25Retriever
from backend.app.retrieval.hybrid import HybridRetriever
from backend.app.retrieval.reranker import LocalReranker
from rank_bm25 import BM25Plus

def test_bm25_retriever():
    retriever = BM25Retriever()
    chunks = [
        DocumentChunk(id="c1", document_id="d1", kb_id="k1", document_version=1, chunk_index=0, page_number=1, text="Error code ERR_SOCKET_TIMEOUT occurred in cluster.", token_count=10),
        DocumentChunk(id="c2", document_id="d1", kb_id="k1", document_version=1, chunk_index=1, page_number=1, text="Overview of distributed storage systems and consensus.", token_count=10)
    ]
    tokens = [retriever._tokenize(c.text) for c in chunks]
    retriever._cached_bm25["k1_v1"] = (BM25Plus(tokens), chunks)
    
    results = retriever.retrieve("k1", 1, "ERR_SOCKET_TIMEOUT", top_k=2)
    assert len(results) > 0
    assert results[0].id == "c1"

def test_local_reranker():
    reranker = LocalReranker()
    chunks = [
        DocumentChunk(id="c1", document_id="d1", kb_id="k1", document_version=1, chunk_index=0, page_number=1, text="General python syntax and loop control structures.", token_count=10, score=0.8),
        DocumentChunk(id="c2", document_id="d1", kb_id="k1", document_version=1, chunk_index=1, page_number=1, text="KV cache reduces memory bandwidth during auto-regressive decoding.", token_count=10, score=0.6)
    ]
    reranked = reranker.rerank("Explain KV cache decoding memory", chunks, top_n=1)
    assert len(reranked) == 1
    assert reranked[0].id == "c2"
