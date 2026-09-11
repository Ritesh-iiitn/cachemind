# CacheMind Technical Architecture & Systems Engineering Reference

## 1. Executive Overview & Architecture
CacheMind is an adaptive Agentic RAG execution engine and LLM inference gateway engineered to minimize compute costs, memory bandwidth consumption, and latency while preserving strict answer faithfulness. 

Traditional RAG architectures execute a naive retrieval-then-generation pipeline for every request, regardless of query repetition, semantic proximity, or structural complexity. CacheMind introduces a five-tier multi-layer caching architecture combined with adaptive query routing and automated verification.

## 2. Multi-Layer Caching Tiers

### Layer 1: Deterministic Exact Response Cache
- **Storage**: Redis or In-Memory Key-Value Store.
- **Key Formulation**: `SHA256("exact:" + kb_id + ":v" + kb_version + ":" + model_id + ":" + normalize(query))`
- **Query Normalization**: Strips superfluous whitespace, converts text to lowercase, and removes invariant punctuation.
- **Latency SLA**: Sub-millisecond (< 1 ms).

### Layer 2: Vector Semantic Response Cache
- **Storage**: FAISS IndexFlatIP cosine similarity matrix.
- **Threshold Policy**: Queries with cosine similarity $\ge 0.88$ are candidate hits.
- **False-Positive Entity Guardrail**: Before returning a semantic cache hit, an entity and number extraction check verifies that named entities, error codes, and numerical identifiers match the cached query.
- **Latency SLA**: 2 - 8 ms.

### Layer 3: Vector Embedding Cache
- **Mechanism**: Local embedding cache storing SHA256 hashes of text chunks and query strings to prevent redundant matrix multiplications in `all-MiniLM-L6-v2`.

### Layer 4: Retrieval Result Cache
- **Mechanism**: Caches retrieved document chunks and similarity scores per `(query, kb_version, retrieval_strategy, top_k)`.
- **Latency Savings**: Eliminates disk I/O and FAISS search latency on subsequent queries requiring novel answer synthesis.

### Layer 5: Prefix Prompt Cache
- **Mechanism**: Detects repeated system instruction prefixes, agent tool signatures, and shared context headers to leverage KV prefill sharing.

## 3. Adaptive Retrieval Strategies

### Dense Search (FAISS IndexFlatIP)
- Ideal for conceptual queries, paraphrased semantic intent, and abstract definitions.

### Keyword Search (BM25Plus)
- High-precision inverted index retrieval for exact error codes, configuration keys, numbers, and technical symbols.

### Hybrid Search (Reciprocal Rank Fusion)
- Fuses Dense and BM25 candidate ranks using the RRF formula:
  $$RRF(d) = \sum_{m \in \{dense, bm25\}} \frac{w_m}{60 + r_m(d)}$$

### Cross-Encoder Local Reranker
- Post-retrieval scoring model refining candidate relevance before context assembly.

## 4. Model Routing & Token Optimization
- **Small Model (Qwen-0.5B / Fast)**: Factual definitions, single-document entity lookup.
- **Medium Model (Qwen-3B / Standard)**: Explanations, structured synthesis, standard RAG.
- **Large Model (Qwen-7B / Reasoning)**: Multi-hop reasoning, comparative document analysis, contradiction detection.

## 5. KV Cache & Attention Complexity
Autoregressive language models compute self-attention using Queries ($Q$), Keys ($K$), and Values ($V$).
- **Naive Attention (No KV Cache)**: At each generation step $t$, the full attention matrix is computed from scratch over length $N = T_{prompt} + t$, resulting in $O(N^2)$ memory bandwidth traffic and quadratic compute.
- **KV Cached Attention**: Past $K$ and $V$ projection vectors are stored in GPU/CPU memory, allowing each new token to compute $Q_{new} \cdot K_{cached}^T$ in $O(1)$ constant time per decode step.
