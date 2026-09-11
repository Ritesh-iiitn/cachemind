import logging
from typing import Dict, Any
from backend.app.cache.exact_cache import exact_cache
from backend.app.cache.semantic_cache import semantic_cache
from backend.app.cache.retrieval_cache import retrieval_cache

logger = logging.getLogger("cachemind.invalidation")

class CacheInvalidator:
    """
    Coordinates atomic invalidation across all multi-layer caching tiers.
    """
    @classmethod
    def invalidate_knowledge_base(cls, kb_id: str) -> Dict[str, Any]:
        """
        Purge all cached entries for a given knowledge base across Exact, Semantic,
        and Retrieval tiers.
        """
        logger.info(f"Triggering atomic cache invalidation for Knowledge Base: {kb_id}")
        exact_purged = exact_cache.invalidate_kb(kb_id)
        semantic_purged = semantic_cache.invalidate_kb(kb_id)
        retrieval_purged = retrieval_cache.invalidate_kb(kb_id)
        
        return {
            "kb_id": kb_id,
            "status": "invalidated",
            "exact_cache_purged": exact_purged,
            "semantic_cache_purged": semantic_purged,
            "retrieval_cache_purged": retrieval_purged,
            "total_purged": exact_purged + semantic_purged + retrieval_purged
        }

    @classmethod
    def flush_all(cls) -> Dict[str, Any]:
        """Global cache flush."""
        logger.warning("Flushing all cache tiers globally.")
        exact_count = len(exact_cache._store)
        semantic_count = len(semantic_cache.items)
        retrieval_count = len(retrieval_cache._store)
        
        exact_cache._store.clear()
        semantic_cache.items.clear()
        semantic_cache._rebuild_index()
        retrieval_cache._store.clear()
        
        return {
            "status": "flushed_all",
            "exact_purged": exact_count,
            "semantic_purged": semantic_count,
            "retrieval_purged": retrieval_count
        }

invalidator = CacheInvalidator()
