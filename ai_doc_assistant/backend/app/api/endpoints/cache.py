import time
from typing import List, Dict, Any
from fastapi import APIRouter, Query, status
from backend.app.models.schemas import CacheStatsResponse, CacheEntryItem
from backend.app.cache.exact_cache import exact_cache
from backend.app.cache.semantic_cache import semantic_cache
from backend.app.cache.retrieval_cache import retrieval_cache
from backend.app.cache.prefix_cache import prefix_cache
from backend.app.cache.invalidation import invalidator

router = APIRouter()

@router.get("/stats", response_model=CacheStatsResponse)
async def get_cache_stats():
    total_reqs = (
        exact_cache.hits + exact_cache.misses +
        semantic_cache.hits +
        retrieval_cache.hits
    )
    total_hits = exact_cache.hits + semantic_cache.hits + retrieval_cache.hits + prefix_cache.hits
    hit_rate = (total_hits / max(1, total_reqs)) * 100.0

    return CacheStatsResponse(
        total_requests=total_reqs,
        total_exact_hits=exact_cache.hits,
        total_semantic_hits=semantic_cache.hits,
        total_retrieval_hits=retrieval_cache.hits,
        total_prefix_hits=prefix_cache.hits,
        total_misses=exact_cache.misses,
        overall_hit_rate=round(hit_rate, 2),
        llm_calls_avoided=exact_cache.hits + semantic_cache.hits,
        total_tokens_saved=(exact_cache.hits + semantic_cache.hits) * 350 + prefix_cache.total_prefill_tokens_saved,
        estimated_compute_saved_pct=round(min(95.0, hit_rate * 0.85), 2),
        exact_cache_size=len(exact_cache._store),
        semantic_cache_size=len(semantic_cache.items),
        retrieval_cache_size=len(retrieval_cache._store)
    )

@router.get("/entries", response_model=List[CacheEntryItem])
async def list_cache_entries(limit: int = Query(50, ge=1, le=200)):
    items: List[CacheEntryItem] = []
    now = time.time()

    # Exact cache items
    for key, entry in list(exact_cache._store.items())[:limit]:
        ans = entry.value.get("answer", "")
        items.append(
            CacheEntryItem(
                key=key[:16] + "...",
                tier="L1 Exact Cache",
                query_snippet=ans[:60] + "..." if len(ans) > 60 else ans,
                created_at=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry.created_at)),
                ttl_remaining_seconds=max(0, int(entry.expires_at - now)),
                hit_count=entry.hit_count,
                size_bytes=len(str(entry.value))
            )
        )

    # Semantic cache items
    for sem in list(semantic_cache.items)[:limit]:
        items.append(
            CacheEntryItem(
                key=f"sem_{sem.item_id}",
                tier="L2 Semantic Cache",
                query_snippet=sem.query[:60],
                created_at=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(sem.created_at)),
                ttl_remaining_seconds=max(0, int(sem.expires_at - now)),
                hit_count=sem.hit_count,
                size_bytes=len(str(sem.response_data))
            )
        )

    # Retrieval cache items
    for key, rentry in list(retrieval_cache._store.items())[:limit]:
        items.append(
            CacheEntryItem(
                key=key[:16] + "...",
                tier="L4 Retrieval Cache",
                query_snippet=f"{len(rentry.chunks)} chunks stored",
                created_at=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(rentry.created_at)),
                ttl_remaining_seconds=max(0, int(rentry.expires_at - now)),
                hit_count=rentry.hit_count,
                size_bytes=len(str(rentry.chunks))
            )
        )

    return items[:limit]

@router.post("/invalidate/{kb_id}")
async def invalidate_kb_cache(kb_id: str):
    return invalidator.invalidate_knowledge_base(kb_id)

@router.post("/flush")
async def flush_all_caches():
    return invalidator.flush_all()
