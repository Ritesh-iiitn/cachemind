import re
import logging
from typing import List, Dict, Any, Tuple
from rank_bm25 import BM25Okapi, BM25Plus
from backend.app.models.schemas import DocumentChunk
from backend.app.ingestion.vector_store import VectorStore

logger = logging.getLogger("cachemind.retrieval.bm25")

class BM25Retriever:
    """
    Exact keyword BM25 retrieval for high-precision entity and identifier matching.
    Uses BM25Plus for strict positive lower-bounded scoring on keyword hits.
    """
    def __init__(self):
        self._cached_bm25: Dict[str, Tuple[BM25Plus, List[DocumentChunk]]] = {}

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return re.findall(r"\b\w+\b", text.lower())

    def _get_or_build_index(self, kb_id: str, kb_version: int) -> Tuple[BM25Plus, List[DocumentChunk]]:
        cache_key = f"{kb_id}_v{kb_version}"
        if cache_key in self._cached_bm25:
            return self._cached_bm25[cache_key]

        vstore = VectorStore(kb_id=kb_id, kb_version=kb_version)
        chunks = [DocumentChunk(**c) for c in vstore.chunks_meta]

        if not chunks:
            bm25 = BM25Plus([["empty"]])
            self._cached_bm25[cache_key] = (bm25, [])
            return bm25, []

        corpus_tokens = [self._tokenize(c.text) for c in chunks]
        bm25 = BM25Plus(corpus_tokens)
        self._cached_bm25[cache_key] = (bm25, chunks)
        return bm25, chunks

    def retrieve(self, kb_id: str, kb_version: int, query: str, top_k: int = 5) -> List[DocumentChunk]:
        bm25, chunks = self._get_or_build_index(kb_id, kb_version)
        if not chunks:
            return []

        q_tokens = self._tokenize(query)
        if not q_tokens:
            return []

        scores = bm25.get_scores(q_tokens)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

        results: List[DocumentChunk] = []
        for idx in top_indices:
            if scores[idx] > 0.0:
                chunk = chunks[idx].model_copy()
                chunk.score = float(scores[idx])
                chunk.retrieval_method = "bm25"
                results.append(chunk)

        logger.info(f"[BM25Retriever] Query: '{query[:30]}...' -> Found {len(results)} chunks.")
        return results

bm25_retriever = BM25Retriever()
