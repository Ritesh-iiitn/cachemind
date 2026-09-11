import logging
from typing import List, Dict
from backend.app.models.schemas import DocumentChunk
from backend.app.retrieval.dense import dense_retriever
from backend.app.retrieval.bm25 import bm25_retriever

logger = logging.getLogger("cachemind.retrieval.hybrid")

class HybridRetriever:
    """
    Hybrid Search combining Dense Vector Search and BM25 Keyword Search
    using Reciprocal Rank Fusion (RRF).
    """
    def __init__(self, rrf_k: int = 60):
        self.rrf_k = rrf_k

    def retrieve(
        self,
        kb_id: str,
        kb_version: int,
        query: str,
        top_k: int = 5,
        dense_weight: float = 0.5,
        bm25_weight: float = 0.5
    ) -> List[DocumentChunk]:
        # Fetch candidate pools
        dense_results = dense_retriever.retrieve(kb_id, kb_version, query, top_k=top_k * 2)
        bm25_results = bm25_retriever.retrieve(kb_id, kb_version, query, top_k=top_k * 2)

        rrf_scores: Dict[str, float] = {}
        chunk_map: Dict[str, DocumentChunk] = {}

        # Process Dense Ranks
        for rank, chunk in enumerate(dense_results, start=1):
            chunk_map[chunk.id] = chunk
            rrf_scores[chunk.id] = rrf_scores.get(chunk.id, 0.0) + (dense_weight / (self.rrf_k + rank))

        # Process BM25 Ranks
        for rank, chunk in enumerate(bm25_results, start=1):
            if chunk.id not in chunk_map:
                chunk_map[chunk.id] = chunk
            rrf_scores[chunk.id] = rrf_scores.get(chunk.id, 0.0) + (bm25_weight / (self.rrf_k + rank))

        # Sort by merged RRF score
        sorted_chunk_ids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)[:top_k]

        merged_results: List[DocumentChunk] = []
        for cid in sorted_chunk_ids:
            chunk = chunk_map[cid].model_copy()
            chunk.score = round(rrf_scores[cid], 5)
            chunk.retrieval_method = "hybrid_rrf"
            merged_results.append(chunk)

        logger.info(f"[HybridRetriever] Query: '{query[:30]}...' -> Merged {len(merged_results)} chunks.")
        return merged_results

hybrid_retriever = HybridRetriever()
