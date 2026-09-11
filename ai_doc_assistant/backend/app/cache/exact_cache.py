import hashlib
import json
import re
import time
import logging
from typing import Optional, Dict, Any, Tuple
from backend.app.core.config import settings

logger = logging.getLogger("cachemind.exact_cache")

class ExactCacheEntry:
    def __init__(self, key: str, value: Dict[str, Any], ttl_seconds: int = 86400):
        self.key = key
        self.value = value
        self.created_at = time.time()
        self.expires_at = self.created_at + ttl_seconds
        self.hit_count = 0
        self.last_accessed = self.created_at

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def touch(self) -> None:
        self.hit_count += 1
        self.last_accessed = time.time()

class ExactResponseCache:
    """
    Tier 1 Exact Response Cache with deterministic request normalization,
    version-isolated SHA-256 keys, and LRU eviction.
    """
    def __init__(self, max_entries: int = 5000):
        self.max_entries = max_entries
        self._store: Dict[str, ExactCacheEntry] = {}
        self.hits = 0
        self.misses = 0

    @staticmethod
    def normalize_query(query: str) -> str:
        # Lowercase, trim whitespace, normalize punctuation
        cleaned = query.strip().lower()
        cleaned = re.sub(r"[^\w\s]", "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned

    def compute_key(self, kb_id: str, kb_version: int, query: str) -> str:
        norm_q = self.normalize_query(query)
        payload = f"exact:{kb_id}:v{kb_version}:{norm_q}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get(self, kb_id: str, kb_version: int, query: str) -> Optional[Dict[str, Any]]:
        key = self.compute_key(kb_id, kb_version, query)
        entry = self._store.get(key)
        
        if entry is None:
            self.misses += 1
            return None
            
        if entry.is_expired():
            del self._store[key]
            self.misses += 1
            return None
            
        entry.touch()
        self.hits += 1
        logger.info(f"[ExactCache HIT] Key: {key[:8]}... Hits: {entry.hit_count}")
        return entry.value

    def put(self, kb_id: str, kb_version: int, query: str, value: Dict[str, Any], ttl_seconds: Optional[int] = None) -> str:
        if len(self._store) >= self.max_entries:
            self._evict_lru()
            
        ttl = ttl_seconds or settings.EXACT_CACHE_TTL_SECONDS
        key = self.compute_key(kb_id, kb_version, query)
        self._store[key] = ExactCacheEntry(key=key, value=value, ttl_seconds=ttl)
        logger.info(f"[ExactCache PUT] Key: {key[:8]}... Total entries: {len(self._store)}")
        return key

    def _evict_lru(self) -> None:
        if not self._store:
            return
        lru_key = min(self._store.keys(), key=lambda k: self._store[k].last_accessed)
        del self._store[lru_key]

    def invalidate_kb(self, kb_id: str) -> int:
        purged = 0
        keys_to_remove = []
        for k, v in self._store.items():
            if v.value.get("kb_id") == kb_id:
                keys_to_remove.append(k)
        for k in keys_to_remove:
            del self._store[k]
            purged += 1
        return purged

    def get_stats(self) -> Dict[str, Any]:
        total = self.hits + self.misses
        hit_rate = (self.hits / total) if total > 0 else 0.0
        return {
            "tier": "Exact Response Cache (L1)",
            "entries_count": len(self._store),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 4),
            "max_entries": self.max_entries
        }

exact_cache = ExactResponseCache()
