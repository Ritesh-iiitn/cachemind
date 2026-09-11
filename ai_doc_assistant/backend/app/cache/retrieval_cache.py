import hashlib
import time
import logging
from typing import Optional, Dict, Any, List, Tuple
from backend.app.core.config import settings
from backend.app.models.schemas import DocumentChunk

logger = logging.getLogger("cachemind.retrieval_cache")

class RetrievalCacheEntry:
    def __init__(self, key: str, kb_id: str, chunks: List[Dict[str, Any]], ttl_seconds: int = 43200):
        self.key = key
        self.kb_id = kb_id
        self.chunks = chunks
        self.created_at = time.time()
        self.expires_at = self.created_at + ttl_seconds
        self.hit_count = 0

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

class RetrievalResultCache:
    """
    Tier 4 Retrieval Result Cache that caches retrieved chunks, scores,
    and metadata per (query + kb_version + strategy + top_k).
    """
    def __init__(self, max_entries: int = 5000):
        self.max_entries = max_entries
        self._store: Dict[str, RetrievalCacheEntry] = {}
        self.hits = 0
        self.misses = 0

    def compute_key(self, kb_id: str, kb_version: int, strategy: str, top_k: int, query: str) -> str:
        norm_q = query.strip().lower()
        payload = f"retrieval:{kb_id}:v{kb_version}:{strategy}:{top_k}:{norm_q}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get(self, kb_id: str, kb_version: int, strategy: str, top_k: int, query: str) -> Optional[List[DocumentChunk]]:
        key = self.compute_key(kb_id, kb_version, strategy, top_k, query)
        entry = self._store.get(key)
        
        if entry is None:
            self.misses += 1
            return None
            
        if entry.is_expired():
            del self._store[key]
            self.misses += 1
            return None
            
        entry.hit_count += 1
        self.hits += 1
        logger.info(f"[RetrievalCache HIT] Key: {key[:8]}... Chunks: {len(entry.chunks)}")
        return [DocumentChunk(**c) for c in entry.chunks]

    def put(
        self,
        kb_id: str,
        kb_version: int,
        strategy: str,
        top_k: int,
        query: str,
        chunks: List[DocumentChunk],
        ttl_seconds: Optional[int] = None
    ) -> str:
        if len(self._store) >= self.max_entries:
            # Evict oldest 100 entries
            for k in list(self._store.keys())[:100]:
                del self._store[k]
                
        key = self.compute_key(kb_id, kb_version, strategy, top_k, query)
        ttl = ttl_seconds or settings.RETRIEVAL_CACHE_TTL_SECONDS
        chunks_serialized = [c.model_dump() for c in chunks]
        self._store[key] = RetrievalCacheEntry(key=key, kb_id=kb_id, chunks=chunks_serialized, ttl_seconds=ttl)
        logger.info(f"[RetrievalCache PUT] Key: {key[:8]}... Saved {len(chunks)} chunks.")
        return key

    def invalidate_kb(self, kb_id: str) -> int:
        purged = 0
        keys_to_remove = [k for k, entry in self._store.items() if entry.kb_id == kb_id]
        for k in keys_to_remove:
            del self._store[k]
            purged += 1
        return purged

    def get_stats(self) -> Dict[str, Any]:
        total = self.hits + self.misses
        hit_rate = (self.hits / total) if total > 0 else 0.0
        return {
            "tier": "Retrieval Result Cache (L4)",
            "entries_count": len(self._store),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 4),
            "max_entries": self.max_entries
        }

retrieval_cache = RetrievalResultCache()
