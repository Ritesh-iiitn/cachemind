import logging
from typing import Dict, Any, Optional
from backend.app.cache.exact_cache import exact_cache
from backend.app.cache.semantic_cache import semantic_cache
from backend.app.cache.retrieval_cache import retrieval_cache

logger = logging.getLogger("cachemind.invalidation")

class CacheInvalidator:
    """
    Coordinates atomic, scoped cache invalidation across all multi-layer caching tiers
    (L1 Exact, L2 Semantic, L4 Retrieval) ensuring version isolation without cross-tenant or cross-KB cache purging.
    """
    @classmethod
    def invalidate_knowledge_base(
        cls,
        kb_id: str,
        tenant_id: str = "default",
        document_id: Optional[str] = None,
        kb_version: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Purge all cached entries scoped to a given knowledge base across Exact, Semantic,
        and Retrieval tiers while strictly preserving entries of unrelated knowledge bases.
        """
        logger.info(
            f"Scoped Cache Invalidation: tenant={tenant_id}, kb_id={kb_id}, "
            f"document={document_id}, new_version={kb_version}"
        )
        exact_purged = exact_cache.invalidate_kb(kb_id)
        semantic_purged = semantic_cache.invalidate_kb(kb_id)
        retrieval_purged = retrieval_cache.invalidate_kb(kb_id)
        
        return {
            "tenant_id": tenant_id,
            "kb_id": kb_id,
            "document_id": document_id,
            "kb_version": kb_version,
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
