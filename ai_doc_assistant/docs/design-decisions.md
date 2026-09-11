# CacheMind Architectural Design Decisions (ADR)

## ADR-001: Version-Bounded Composite Cache Keys
- **Context**: Updating or deleting a document must not return stale answers from L1, L2, or L4 caches.
- **Decision**: All cache keys are bound to `kb_version`. When documents change, `kb_version` increments, automatically isolating stale keys and preventing cache pollution without requiring costly full scans.

## ADR-002: Two-Stage Entity Guardrails for Semantic Cache
- **Context**: Pure vector similarity ($\ge 0.88$) produces false positives on structural duplicates with differing entity targets (e.g. Model X vs Model Y).
- **Decision**: Implemented an Entity Overlap Guardrail before approving an L2 Semantic Cache hit. If named entities differ, the request is treated as a cache miss and executed cold.

## ADR-003: Hybrid Retrieval with Reciprocal Rank Fusion (RRF)
- **Context**: Dense vector search struggles on exact error codes and IDs, while BM25 struggles on semantic paraphrase.
- **Decision**: Hybrid search executes both FAISS and BM25Plus, merging candidate rankings with $RRF(d) = \sum \frac{w_m}{60 + r_m(d)}$.

## ADR-004: Dual C++ & Python Implementation for Attention & KV Profiling
- **Context**: Application caching and KV inference caching are frequently conflated in conversational AI literature.
- **Decision**: Built a dedicated C++ engine (`cpp/kv_benchmark/kv_cache_sim.cpp`) and companion Python profiler (`backend/app/inference/kv_experiments.py`) to provide rigorous mathematical proof of quadratic $O(N^2)$ memory bandwidth versus constant $O(1)$ KV decode stepping.
