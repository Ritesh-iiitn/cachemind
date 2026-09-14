const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api/v1";

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
  async deleteKnowledgeBase(kbId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/kb/${kbId}`, { method: "DELETE" });
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
  },

  // Job Queue & Asynchronous Ingestion
  async listJobs(params?: {
    status?: string;
    task_type?: string;
    document_id?: string;
    knowledge_base_id?: string;
    page?: number;
    page_size?: number;
  }): Promise<JobListResponse> {
    const query = new URLSearchParams();
    if (params?.status) query.append("status", params.status);
    if (params?.task_type) query.append("task_type", params.task_type);
    if (params?.document_id) query.append("document_id", params.document_id);
    if (params?.knowledge_base_id) query.append("knowledge_base_id", params.knowledge_base_id);
    if (params?.page) query.append("page", params.page.toString());
    if (params?.page_size) query.append("page_size", params.page_size.toString());

    const res = await fetch(`${API_BASE}/jobs?${query.toString()}`);
    return res.json();
  },

  async getJob(jobId: string): Promise<IngestionJob> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}`);
    return res.json();
  },

  async getQueueStats(): Promise<QueueStats> {
    const res = await fetch(`${API_BASE}/queue/stats`);
    return res.json();
  },

  async cancelJob(jobId: string, reason?: string): Promise<IngestionJob> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/cancel`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason })
    });
    return res.json();
  },

  async retryJob(jobId: string, resetAttempts: boolean = true): Promise<IngestionJob> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/retry`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reset_attempts: resetAttempts })
    });
    return res.json();
  },

  async uploadDocumentAsync(
    kbId: string,
    file: File,
    priority: number = 5
  ): Promise<DocumentUploadAsyncResponse> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("knowledge_base_id", kbId);
    formData.append("priority", priority.toString());

    const res = await fetch(`${API_BASE}/documents/upload`, {
      method: "POST",
      body: formData
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Upload failed" }));
      throw new Error(err.detail || "Upload failed");
    }
    return res.json();
  }
};

export type JobStatus = "QUEUED" | "PROCESSING" | "RETRYING" | "COMPLETED" | "FAILED" | "CANCELLED";

export interface RetryHistoryItem {
  attempt: number;
  timestamp: string;
  error_code?: string;
  error_message?: string;
  delay_seconds: number;
}

export interface IngestionJob {
  id: string;
  job_id: string;
  tenant_id: string;
  document_id?: string;
  knowledge_base_id?: string;
  document_name?: string;
  task_type: string;
  status: JobStatus;
  priority: number;
  progress: number;
  current_stage: string;
  total_items: number;
  processed_items: number;
  attempt_count: number;
  max_attempts: number;
  error_code?: string;
  error_message?: string;
  worker_id?: string;
  queue_wait_time_ms?: number;
  processing_time_ms?: number;
  metadata: Record<string, any>;
  retry_history: RetryHistoryItem[];
  queue_position?: number;
  estimated_wait_time_ms?: number;
  created_at: string;
  started_at?: string;
  updated_at: string;
  completed_at?: string;
}

export interface JobListResponse {
  jobs: IngestionJob[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface QueueStats {
  queued: number;
  processing: number;
  completed_today: number;
  failed_today: number;
  cancelled_today: number;
  active_workers: number;
  average_wait_time_ms: number;
  average_processing_time_ms: number;
  queue_depth: number;
  success_rate_pct: number;
  retry_rate_pct: number;
  worker_utilization_pct: number;
}

export interface DocumentUploadAsyncResponse {
  document_id: string;
  job_id: string;
  status: string;
  message: string;
}

