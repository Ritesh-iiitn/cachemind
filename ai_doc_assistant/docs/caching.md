# CacheMind Multi-Layer Caching & Consistency Guide

## Caching Taxonomy

CacheMind implements a 5-tier caching hierarchy operating across different stages of the request lifecycle:

| Layer | Tier Name | Storage Mechanism | Target Object | Lookup Latency |
| :--- | :--- | :--- | :--- | :--- |
| **L1** | Exact Response Cache | Redis / In-Memory Store | Complete Final Answer | $< 1$ ms |
| **L2** | Semantic Response Cache | FAISS IndexFlatIP + Guardrail | Final Answer ($\ge 0.88$ sim) | $2 - 8$ ms |
| **L3** | Embedding Cache | In-Memory Hash Map | 384-dim Float32 Vector | $< 0.1$ ms |
| **L4** | Retrieval Result Cache | Version-keyed Hash Store | Candidate Chunk IDs & Scores | $< 1$ ms |
| **L5** | Prefix Prompt Cache | Prefix Registry | KV Prefill Computation State | $< 0.5$ ms |

---

## 1. Layer 1: Exact Response Cache
- **Key Formulation**:
  ```python
  Key = SHA256(f"exact:{kb_id}:v{kb_version}:{normalize(query)}")
  ```
- **Query Normalization**:
  1. Trim leading and trailing whitespace.
  2. Lowercase transformation.
  3. Strip punctuation and collapse internal whitespace.

---

## 2. Layer 2: Semantic Response Cache & False-Positive Guardrail
High cosine similarity ($\ge 0.88$) in vector space does not guarantee semantic equivalence. For example:
- *"What are the advantages of Architecture A?"*
- *"What are the advantages of Architecture B?"*

These two queries have high vector similarity because of shared syntactic structures. To avoid false positives, CacheMind applies a **Two-Stage Verification Guardrail**:
1. **Cosine Similarity Check**: Cosine similarity $\ge \tau$ (default $\tau = 0.88$).
2. **Entity & Identifier Overlap**: Tokenizes named entities, numerical codes, and acronyms from both queries. If the entity overlap is below $40\%$, the semantic cache hit is rejected and routed to cold execution.

---

## 3. Layer 4: Retrieval Result Cache
When a query requires novel answer synthesis (e.g. customized user formatting), the retrieval step can still be bypassed if the exact set of chunks was retrieved previously for that query.
- **Key Formulation**:
  ```python
  Key = SHA256(f"retrieval:{kb_id}:v{kb_version}:{strategy}:{top_k}:{normalize(query)}")
  ```

---

## 4. Cache Invalidation & Version Isolation
When a document is uploaded, updated, or deleted from a Knowledge Base:
1. The `knowledge_bases.version` integer is atomically incremented in SQLite ($v \to v+1$).
2. All new queries compute cache keys with the new version, rendering stale entries unreachable.
3. The `CacheInvalidator` triggers synchronous purging across all active in-memory stores for the targeted `kb_id`.
