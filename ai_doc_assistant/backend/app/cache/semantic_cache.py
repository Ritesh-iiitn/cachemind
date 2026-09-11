import time
import logging
import re
from typing import Optional, Dict, Any, List, Tuple
import numpy as np
import faiss
from backend.app.core.config import settings
from backend.app.ingestion.embedder import embedding_engine

logger = logging.getLogger("cachemind.semantic_cache")

class SemanticCacheItem:
    def __init__(
        self,
        item_id: str,
        kb_id: str,
        kb_version: int,
        query: str,
        response_data: Dict[str, Any],
        embedding: np.ndarray,
        ttl_seconds: int = 86400
    ):
        self.item_id = item_id
        self.kb_id = kb_id
        self.kb_version = kb_version
        self.query = query
        self.response_data = response_data
        self.embedding = embedding
        self.created_at = time.time()
        self.expires_at = self.created_at + ttl_seconds
        self.hit_count = 0
        self.entities = self._extract_key_tokens(query)

    @staticmethod
    def _extract_key_tokens(text: str) -> set:
        # Extract alphanumeric words and numbers for false-positive protection
        words = re.findall(r"\b[a-zA-Z0-9_-]{3,}\b", text.lower())
        return set(words)

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

class SemanticResponseCache:
    """
    Tier 2 Semantic Response Cache powered by FAISS vector similarity
    and double-checked with Entity & Intent Guardrails to prevent false-positives.
    """
    def __init__(self, similarity_threshold: float = None):
        self.threshold = similarity_threshold or settings.SEMANTIC_CACHE_SIMILARITY_THRESHOLD
        self.dim = settings.EMBEDDING_DIMENSION
        self.items: List[SemanticCacheItem] = []
        self.index = faiss.IndexFlatIP(self.dim)
        self.hits = 0
        self.misses = 0
        self.false_positives_blocked = 0

    def _rebuild_index(self) -> None:
        self.index = faiss.IndexFlatIP(self.dim)
        if not self.items:
            return
        matrix = np.vstack([item.embedding for item in self.items]).astype("float32")
        self.index.add(matrix)

    def lookup(
        self,
        kb_id: str,
        kb_version: int,
        query: str,
        query_vec: Optional[np.ndarray] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[float]]:
        if not self.items or self.index.ntotal == 0:
            self.misses += 1
            return None, None

        if query_vec is None:
            query_vec = embedding_engine.embed_text(query)

        q_vec = np.ascontiguousarray(query_vec.reshape(1, -1).astype("float32"))
        top_k = min(5, len(self.items))
        scores, indices = self.index.search(q_vec, top_k)

        query_entities = SemanticCacheItem._extract_key_tokens(query)

        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.items):
                continue
                
            item = self.items[idx]
            
            # Check KB ID and Version isolation
            if item.kb_id != kb_id or item.kb_version != kb_version:
                continue
                
            # Check TTL
            if item.is_expired():
                continue
                
            sim = float(score)
            if sim >= self.threshold:
                # Entity Guardrail: Check entity overlap if specific terms/numbers exist
                if query_entities and item.entities:
                    overlap = len(query_entities.intersection(item.entities)) / max(len(query_entities), 1)
                    if overlap < 0.4:
                        # Vectors close, but different entities (e.g. Model X vs Model Y)
                        self.false_positives_blocked += 1
                        logger.info(f"[SemanticCache GUARD] High sim {sim:.3f} but low entity overlap ({overlap:.2f}) between '{query}' and '{item.query}'")
                        continue

                item.hit_count += 1
                self.hits += 1
                logger.info(f"[SemanticCache HIT] Sim: {sim:.4f} Query: '{query}' -> Cached: '{item.query}'")
                return item.response_data, sim

        self.misses += 1
        return None, None

    def put(
        self,
        kb_id: str,
        kb_version: int,
        query: str,
        response_data: Dict[str, Any],
        query_vec: Optional[np.ndarray] = None,
        ttl_seconds: int = 86400
    ) -> str:
        if query_vec is None:
            query_vec = embedding_engine.embed_text(query)

        item_id = f"sem_{len(self.items) + 1}"
        item = SemanticCacheItem(
            item_id=item_id,
            kb_id=kb_id,
            kb_version=kb_version,
            query=query,
            response_data=response_data,
            embedding=query_vec,
            ttl_seconds=ttl_seconds
        )
        
        self.items.append(item)
        vec_norm = np.ascontiguousarray(query_vec.reshape(1, -1).astype("float32"))
        self.index.add(vec_norm)
        
        logger.info(f"[SemanticCache PUT] Query: '{query[:40]}...' Total entries: {len(self.items)}")
        return item_id

    def invalidate_kb(self, kb_id: str) -> int:
        initial_len = len(self.items)
        self.items = [it for it in self.items if it.kb_id != kb_id]
        purged = initial_len - len(self.items)
        if purged > 0:
            self._rebuild_index()
        return purged

    def get_stats(self) -> Dict[str, Any]:
        total = self.hits + self.misses
        hit_rate = (self.hits / total) if total > 0 else 0.0
        return {
            "tier": "Semantic Response Cache (L2)",
            "entries_count": len(self.items),
            "hits": self.hits,
            "misses": self.misses,
            "false_positives_blocked": self.false_positives_blocked,
            "similarity_threshold": self.threshold,
            "hit_rate": round(hit_rate, 4)
        }

semantic_cache = SemanticResponseCache()
