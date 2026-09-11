# CacheMind Architecture & Systems Design

## Overview
CacheMind is an adaptive Agentic RAG execution gateway designed for high-throughput, low-latency, and cost-efficient LLM inference. It integrates multi-layer caching, dynamic query routing, multi-hop query decomposition, cross-encoder reranking, and verification loops to minimize compute overhead while preserving answer fidelity.

---

## High-Level Component Topology

```text
                                 FRONTEND (React + Vite + Tailwind + Lucide + Recharts)
                       [Dashboard | Knowledge Base | Query Playground | Cache Explorer | Benchmark Lab | Inference Lab]
                                                           │
                                                           ▼ (REST API / SSE)
                                              FASTAPI GATEWAY (Asynchronous)
                                                           │
                                                           ▼
                                               QUERY ORCHESTRATOR & TRACER
                                                           │
                                ┌──────────────────────────┴──────────────────────────┐
                                ▼                                                     ▼
                       CACHE-AWARE PLANNER                                   TRACING & METRICS DB
             (Evaluates TTL, KB Version, Latency Budget)                 (SQLite + Structured Events)
                                │
               ┌────────────────┼────────────────┬────────────────┐
               ▼                ▼                ▼                ▼
         [Exact Cache]   [Semantic Cache] [Retrieval Cache] [Prefix Cache]
          (Redis / In-Mem) (FAISS + MiniLM) (Chunk IDs + Meta) (Prompt Prefix)
               │                │                │                │
               └────────────────┼────────────────┴────────────────┘
                                ▼ (On Cache Miss / Partial Miss)
                       AGENTIC RAG STATE GRAPH (LangGraph / State Machine)
                                │
                      Query Intent & Complexity Evaluator
                                │
                      Multi-Hop Query Decomposer
                                │
                      Adaptive Retrieval Selector
                                │
                 ┌──────────────┼──────────────┐
                 ▼              ▼              ▼
           [Dense Search] [BM25 Search] [Hybrid Search]
             (FAISS/Vector) (Rank-BM25)  (RRF / Convex)
                 │              │              │
                 └──────────────┼──────────────┘
                                ▼
                       CROSS-ENCODER RERANKER
                                │
                       CONTEXT BUILDER & AUDITOR
                                │
                          MODEL ROUTER
             (Complexity, Token Budget, Latency SLA)
                                │
                 ┌──────────────┼──────────────┐
                 ▼              ▼              ▼
            Small Model    Medium Model   Large Model
            (Fast/Fact)    (Standard RAG) (Deep Synth)
                 │              │              │
                 └──────────────┼──────────────┘
                                ▼
                  INFERENCE ENGINE (Local Engine)
              (Prefix KV Reuse, Streaming, Fallbacks)
                                │
                         ANSWER SYNTHESIS
                                │
                     QUALITY & CITATION VERIFIER
                         ┌──────┴──────┐
                         ▼             ▼
                      Valid         Invalid
                         │             │
                         │      (Rewrite Query &
                         │       Refine Retrieval)
                         ▼
                CACHE ADMISSION FILTER
             (Frequency, Cost, Stability)
                         │
                         ▼
                RETURN TRACED RESPONSE
```

---

## Core Subsystems

### 1. Multi-Tier Cache Layer
- **Layer 1 (Exact Hash Cache)**: $O(1)$ lookup via normalized SHA-256 hash. Sub-millisecond response time.
- **Layer 2 (Semantic Vector Cache)**: FAISS IndexFlatIP cosine similarity matrix with false-positive entity guardrails ($\tau \ge 0.88$).
- **Layer 3 (Vector Embedding Cache)**: Avoids redundant matrix multiplications for repeated chunk texts and query strings.
- **Layer 4 (Retrieval Result Cache)**: Caches retrieved chunk IDs and scores for dynamic synthesis queries.
- **Layer 5 (Prefix Prompt Cache)**: Identifies shared system instructions and common context prefixes to leverage KV prefill sharing.

### 2. Adaptive Retrieval Engine
- **Dense Vector Search**: FAISS IndexFlatIP cosine similarity search over chunk embeddings.
- **BM25 Keyword Search**: BM25Plus inverted index with positive lower bounds for exact error codes, numbers, and identifiers.
- **Hybrid Search**: Fuses dense and sparse candidate rankings using Reciprocal Rank Fusion (RRF, $k=60$).
- **Cross-Encoder Reranker**: Post-retrieval relevance refinement prior to prompt context assembly.

### 3. Model Routing
- **Small (0.5B)**: Factual definitions, single entity lookup.
- **Medium (3B)**: Structured explanations, standard RAG synthesis.
- **Large (7B)**: Multi-document comparisons, multi-hop reasoning, contradiction analysis.

### 4. Verification & Guardrails
- Compares generated tokens against retrieved chunk terms.
- Ensures citations are grounded and detects hallucinations.
- Bounded retry loop triggers query rewriting and expanded retrieval if initial verification fails.
