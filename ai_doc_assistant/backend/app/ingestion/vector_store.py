import os
import json
import logging
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
import faiss
from backend.app.core.config import settings
from backend.app.models.schemas import DocumentChunk
from backend.app.ingestion.embedder import embedding_engine

logger = logging.getLogger("cachemind.vector_store")

class VectorStore:
    """
    FAISS IndexFlatIP vector store manager with version isolation per Knowledge Base.
    """
    def __init__(self, kb_id: str, kb_version: int = 1):
        self.kb_id = kb_id
        self.kb_version = kb_version
        self.dim = settings.EMBEDDING_DIMENSION
        self.index_dir = settings.VECTOR_STORAGE / f"{kb_id}_v{kb_version}"
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.index_dir / "index.faiss"
        self.meta_file = self.index_dir / "chunks.json"
        
        self.index: Optional[faiss.IndexFlatIP] = None
        self.chunks_meta: List[Dict[str, Any]] = []
        self._load_or_create()

    def _load_or_create(self) -> None:
        if self.index_file.exists() and self.meta_file.exists():
            try:
                self.index = faiss.read_index(str(self.index_file))
                with open(self.meta_file, "r", encoding="utf-8") as f:
                    self.chunks_meta = json.load(f)
                logger.info(f"Loaded FAISS index for {self.kb_id} v{self.kb_version} with {self.index.ntotal} vectors.")
                return
            except Exception as e:
                logger.warning(f"Failed to load index for {self.kb_id}, recreating: {e}")
                
        self.index = faiss.IndexFlatIP(self.dim)
        self.chunks_meta = []

    def save(self) -> None:
        if self.index is not None:
            faiss.write_index(self.index, str(self.index_file))
            with open(self.meta_file, "w", encoding="utf-8") as f:
                json.dump(self.chunks_meta, f, ensure_ascii=False)
            logger.info(f"Saved FAISS index ({self.index.ntotal} vectors) to {self.index_file}")

    def add_chunks(self, chunks: List[DocumentChunk]) -> None:
        if not chunks:
            return
            
        texts = [c.text for c in chunks]
        embeddings = embedding_engine.embed_batch(texts)
        
        if self.index is None:
            self.index = faiss.IndexFlatIP(self.dim)
            
        self.index.add(embeddings)
        
        for c in chunks:
            self.chunks_meta.append(c.model_dump())
            
        self.save()

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Tuple[DocumentChunk, float]]:
        if self.index is None or self.index.ntotal == 0:
            return []
            
        query_vector = np.ascontiguousarray(query_vector.reshape(1, -1).astype("float32"))
        k = min(top_k, self.index.ntotal)
        scores, indices = self.index.search(query_vector, k)
        
        results: List[Tuple[DocumentChunk, float]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(self.chunks_meta):
                chunk_data = self.chunks_meta[idx].copy()
                chunk_data["score"] = float(score)
                chunk_data["retrieval_method"] = "dense_faiss"
                results.append((DocumentChunk(**chunk_data), float(score)))
                
        return results

    def clear(self) -> None:
        self.index = faiss.IndexFlatIP(self.dim)
        self.chunks_meta = []
        if self.index_file.exists():
            self.index_file.unlink()
        if self.meta_file.exists():
            self.meta_file.unlink()
