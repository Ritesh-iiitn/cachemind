import logging
from typing import List, Tuple
from backend.app.models.schemas import DocumentChunk
from backend.app.ingestion.vector_store import VectorStore
from backend.app.ingestion.embedder import embedding_engine

logger = logging.getLogger("cachemind.retrieval.dense")

class DenseRetriever:
    """
    Dense vector search using FAISS and cosine similarity embeddings.
    """
    def __init__(self):
        pass

    def retrieve(self, kb_id: str, kb_version: int, query: str, top_k: int = 5) -> List[DocumentChunk]:
        query_vec = embedding_engine.embed_text(query)
        vstore = VectorStore(kb_id=kb_id, kb_version=kb_version)
        results = vstore.search(query_vec, top_k=top_k)
        
        chunks = []
        for chunk, score in results:
            chunk.score = score
            chunk.retrieval_method = "dense_faiss"
            chunks.append(chunk)
            
        logger.info(f"[DenseRetriever] Query: '{query[:30]}...' -> Found {len(chunks)} chunks.")
        return chunks

dense_retriever = DenseRetriever()
