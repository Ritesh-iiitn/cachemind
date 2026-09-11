from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime

# ==================== KNOWLEDGE BASE & DOCUMENTS ====================

class KnowledgeBaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None

class KnowledgeBaseResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    version: int
    created_at: str
    updated_at: str
    document_count: Optional[int] = 0
    chunk_count: Optional[int] = 0

class DocumentChunk(BaseModel):
    id: str
    document_id: str
    kb_id: str
    document_version: int
    chunk_index: int
    page_number: Optional[int] = 1
    section: Optional[str] = None
    text: str
    token_count: int
    score: Optional[float] = None
    retrieval_method: Optional[str] = None

class DocumentResponse(BaseModel):
    id: str
    kb_id: str
    filename: str
    file_type: str
    file_size: int
    version: int
    status: str
    chunk_count: int
    content_hash: str
    created_at: str
    updated_at: str

# ==================== CACHE & PLANNING ====================

class CacheStatus(BaseModel):
    exact_cache_hit: bool = False
    semantic_cache_hit: bool = False
    retrieval_cache_hit: bool = False
    prefix_cache_hit: bool = False
    similarity_score: Optional[float] = None
    cache_tier_matched: Optional[str] = "NONE"
    cached_response_id: Optional[str] = None

class ExecutionPlan(BaseModel):
    plan_id: str
    reason: str
    query_complexity: Literal["simple", "moderate", "complex", "multi_hop"]
    retrieval_strategy: Literal["none", "dense", "bm25", "hybrid"]
    use_reranker: bool
    model_tier: Literal["small", "medium", "large"]
    model_name: str
    verification_required: bool
    estimated_latency_ms: float
    cache_candidates: List[str] = Field(default_factory=list)

class QueryRequest(BaseModel):
    kb_id: str
    query: str = Field(..., min_length=1)
    force_no_cache: bool = False
    force_strategy: Optional[Literal["dense", "bm25", "hybrid"]] = None
    force_model: Optional[Literal["small", "medium", "large"]] = None

class Citation(BaseModel):
    document_id: str
    filename: str
    chunk_id: str
    page_number: Optional[int] = None
    section: Optional[str] = None
    snippet: str

class QueryResponse(BaseModel):
    request_id: str
    query: str
    answer: str
    citations: List[Citation] = Field(default_factory=list)
    execution_plan: ExecutionPlan
    cache_status: CacheStatus
    latency_breakdown_ms: Dict[str, float] = Field(default_factory=dict)
    total_latency_ms: float
    model_used: str
    tokens_generated: int
    tokens_saved: int
    verification_status: Literal["PASSED", "RETRIED", "FAILED", "SKIPPED"]
    steps_executed: List[str] = Field(default_factory=list)

# ==================== OBSERVABILITY & TRACING ====================

class TraceStep(BaseModel):
    step_name: str
    started_at: float
    duration_ms: float
    details: Dict[str, Any] = Field(default_factory=dict)

class ExecutionTrace(BaseModel):
    request_id: str
    kb_id: str
    query: str
    plan_id: str
    exact_cache_hit: bool
    semantic_cache_hit: bool
    retrieval_cache_hit: bool
    prefix_cache_hit: bool
    retrieval_strategy: str
    model_used: str
    verification_status: str
    latency_ms: float
    tokens_generated: int
    tokens_saved: int
    estimated_cost_saved: float
    steps: List[TraceStep] = Field(default_factory=list)
    created_at: str

# ==================== CACHE STATS & METRICS ====================

class CacheEntryItem(BaseModel):
    key: str
    tier: str
    query_snippet: str
    created_at: str
    ttl_remaining_seconds: Optional[int]
    hit_count: int
    size_bytes: int

class CacheStatsResponse(BaseModel):
    total_requests: int
    total_exact_hits: int
    total_semantic_hits: int
    total_retrieval_hits: int
    total_prefix_hits: int
    total_misses: int
    overall_hit_rate: float
    llm_calls_avoided: int
    total_tokens_saved: int
    estimated_compute_saved_pct: float
    exact_cache_size: int
    semantic_cache_size: int
    retrieval_cache_size: int

# ==================== BENCHMARKING ====================

class BenchmarkRunRequest(BaseModel):
    name: str = "Standard RAG vs CacheMind Benchmark"
    kb_id: str
    queries_count: int = Field(default=10, ge=2, le=100)
    workload_type: Literal["uniform", "zipfian_repeated", "complex_multi_hop", "mixed"] = "mixed"

class BenchmarkResultItem(BaseModel):
    query: str
    baseline_latency_ms: float
    optimized_latency_ms: float
    cache_tier: str
    model_used: str
    latency_reduction_pct: float
    tokens_saved: int

class BenchmarkReport(BaseModel):
    id: str
    name: str
    workload_type: str
    total_queries: int
    baseline_p50_ms: float
    baseline_p95_ms: float
    baseline_avg_ms: float
    optimized_p50_ms: float
    optimized_p95_ms: float
    optimized_avg_ms: float
    cache_hit_rate: float
    compute_saved_pct: float
    detailed_results: List[BenchmarkResultItem]
    created_at: str
