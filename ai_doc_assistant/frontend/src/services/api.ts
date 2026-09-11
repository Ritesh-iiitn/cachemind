const API_BASE = "http://localhost:8000/api/v1";

export interface KnowledgeBase {
  id: string;
  name: string;
  description?: string;
  version: number;
  created_at: string;
  updated_at: string;
  document_count?: number;
  chunk_count?: number;
}

export interface DocumentItem {
  id: string;
  kb_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  version: number;
  status: string;
  chunk_count: number;
  content_hash: string;
  created_at: string;
}

export interface Citation {
  document_id: string;
  filename: string;
  chunk_id: string;
  page_number?: number;
  section?: string;
  snippet: string;
}

export interface ExecutionPlan {
  plan_id: string;
  reason: string;
  query_complexity: "simple" | "moderate" | "complex" | "multi_hop";
  retrieval_strategy: "none" | "dense" | "bm25" | "hybrid";
  use_reranker: boolean;
  model_tier: "small" | "medium" | "large";
  model_name: string;
  verification_required: boolean;
  estimated_latency_ms: number;
  cache_candidates: string[];
}

export interface CacheStatus {
  exact_cache_hit: boolean;
  semantic_cache_hit: boolean;
  retrieval_cache_hit: boolean;
  prefix_cache_hit: boolean;
  similarity_score?: number;
  cache_tier_matched?: string;
}

export interface QueryResponse {
  request_id: string;
  query: string;
  answer: string;
  citations: Citation[];
  execution_plan: ExecutionPlan;
  cache_status: CacheStatus;
  latency_breakdown_ms: Record<string, number>;
  total_latency_ms: number;
  model_used: string;
  tokens_generated: number;
  tokens_saved: number;
  verification_status: "PASSED" | "RETRIED" | "FAILED" | "SKIPPED";
  steps_executed: string[];
}

export interface CacheStats {
  total_requests: number;
  total_exact_hits: number;
  total_semantic_hits: number;
  total_retrieval_hits: number;
  total_prefix_hits: number;
  total_misses: number;
  overall_hit_rate: number;
  llm_calls_avoided: number;
  total_tokens_saved: number;
  estimated_compute_saved_pct: number;
  exact_cache_size: number;
  semantic_cache_size: number;
  retrieval_cache_size: number;
}

export interface CacheEntry {
  key: string;
  tier: string;
  query_snippet: string;
  created_at: string;
  ttl_remaining_seconds?: number;
  hit_count: number;
  size_bytes: number;
}

export interface BenchmarkReport {
  id: string;
  name: string;
  workload_type: string;
  total_queries: number;
  baseline_p50_ms: number;
  baseline_p95_ms: number;
  baseline_avg_ms: number;
  optimized_p50_ms: number;
  optimized_p95_ms: number;
  optimized_avg_ms: number;
  cache_hit_rate: number;
  compute_saved_pct: number;
  detailed_results: Array<{
    query: string;
    baseline_latency_ms: number;
    optimized_latency_ms: number;
    cache_tier: string;
    model_used: string;
    latency_reduction_pct: number;
    tokens_saved: number;
  }>;
  created_at: string;
}

export const api = {
  // KB
  async listKnowledgeBases(): Promise<KnowledgeBase[]> {
    const res = await fetch(`${API_BASE}/kb`);
    return res.json();
  },
  async createKnowledgeBase(name: string, description?: string): Promise<KnowledgeBase> {
    const res = await fetch(`${API_BASE}/kb`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, description })
    });
    return res.json();
  },
  async uploadDocument(kbId: string, file: File): Promise<DocumentItem> {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/kb/${kbId}/documents`, {
      method: "POST",
      body: formData
    });
    return res.json();
  },
  async listDocuments(kbId: string): Promise<DocumentItem[]> {
    const res = await fetch(`${API_BASE}/kb/${kbId}/documents`);
    return res.json();
  },
  async deleteDocument(kbId: string, docId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/kb/${kbId}/documents/${docId}`, { method: "DELETE" });
    return res.json();
  },

  // Query
  async executeQuery(kbId: string, query: string, forceNoCache: boolean = false): Promise<QueryResponse> {
    const res = await fetch(`${API_BASE}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kb_id: kbId, query, force_no_cache: forceNoCache })
    });
    return res.json();
  },

  // Cache
  async getCacheStats(): Promise<CacheStats> {
    const res = await fetch(`${API_BASE}/cache/stats`);
    return res.json();
  },
  async listCacheEntries(): Promise<CacheEntry[]> {
    const res = await fetch(`${API_BASE}/cache/entries`);
    return res.json();
  },
  async invalidateKbCache(kbId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/cache/invalidate/${kbId}`, { method: "POST" });
    return res.json();
  },
  async flushAllCaches(): Promise<any> {
    const res = await fetch(`${API_BASE}/cache/flush`, { method: "POST" });
    return res.json();
  },

  // Benchmarking
  async runBenchmark(kbId: string, queriesCount: number = 8, workloadType: string = "mixed"): Promise<BenchmarkReport> {
    const res = await fetch(`${API_BASE}/benchmark/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kb_id: kbId, queries_count: queriesCount, workload_type: workloadType })
    });
    return res.json();
  },
  async listBenchmarkHistory(): Promise<BenchmarkReport[]> {
    const res = await fetch(`${API_BASE}/benchmark/history`);
    return res.json();
  },

  // Inference & KV
  async runKVBenchmark(promptTokens: number, genTokens: number, hiddenDim: number, heads: number): Promise<any> {
    const params = new URLSearchParams({
      prompt_tokens: promptTokens.toString(),
      generated_tokens: genTokens.toString(),
      hidden_dim: hiddenDim.toString(),
      num_heads: heads.toString()
    });
    const res = await fetch(`${API_BASE}/inference/kv-benchmark?${params}`);
    return res.json();
  },

  // Observability
  async listTraces(): Promise<any[]> {
    const res = await fetch(`${API_BASE}/observability/traces`);
    return res.json();
  }
};
