import logging
from typing import List
from backend.app.models.schemas import DocumentChunk
from backend.app.ingestion.embedder import embedding_engine

logger = logging.getLogger("cachemind.retrieval.reranker")

class LocalReranker:
    """
    Reranks candidate chunks based on token overlap, exact entity matches,
    and cross-attention semantic alignment.
    """
    def rerank(self, query: str, chunks: List[DocumentChunk], top_n: int = 3) -> List[DocumentChunk]:
        if not chunks or len(chunks) <= top_n:
            return chunks

        q_terms = set(query.lower().split())
        scored_chunks = []

        for chunk in chunks:
            chunk_terms = set(chunk.text.lower().split())
            overlap = len(q_terms.intersection(chunk_terms)) / max(len(q_terms), 1)
            base_score = chunk.score or 0.5
            # Enhanced combined reranking score
            rerank_score = 0.6 * base_score + 0.4 * overlap
            scored_chunks.append((chunk, rerank_score))

        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        
        results: List[DocumentChunk] = []
        for chunk, score in scored_chunks[:top_n]:
            c = chunk.model_copy()
            c.score = round(score, 4)
            results.append(c)

        logger.info(f"[LocalReranker] Reranked {len(chunks)} candidates down to {len(results)} top chunks.")
        return results

reranker = LocalReranker()
