# CacheMind Benchmarking & Evaluation Methodology

## Benchmarking Goals
The benchmark framework measures the empirical performance differences between **Baseline Naive RAG** (Standard retrieve-then-generate without caching or routing) versus **CacheMind** (Adaptive planning, multi-layer caching, hybrid search, reranking, model routing, verification).

---

## Evaluation Metrics

### 1. Latency Metrics
- **P50 (Median) Latency**: Typical response latency across warm and cold queries.
- **P95 (Tail) Latency**: Latency of complex multi-hop decomposition and cold retrieval queries.
- **Average Latency**: Mean duration across the entire benchmark workload.

### 2. Cache Efficiency Metrics
- **Overall Hit Rate**: $\frac{\text{L1 Hits} + \text{L2 Hits} + \text{L4 Hits} + \text{L5 Hits}}{\text{Total Requests}} \times 100\%$
- **LLM Calls Avoided**: Exact count of queries served entirely from L1/L2 without invoking the neural network.
- **Tokens Saved**: Sum of avoided generation tokens and reused prompt prefill tokens.
- **Compute Cost Saved %**: Percentage reduction in total GPU/CPU compute execution time.

---

## Workload Profiles

1. **Uniform Workload**: Random queries across all indexed documents.
2. **Zipfian / Repeated Workload**: Heavy tail distribution with repeated and semantically paraphrased questions (demonstrating L1/L2 hit rates $\ge 70\%$).
3. **Complex Multi-Hop Workload**: Synthesis and comparison questions triggering query decomposition, hybrid retrieval, and large model routing.
4. **Mixed Production Workload**: Realistic blend of factual lookups, semantic variations, and deep synthesis queries.
