from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    RETRYING = "RETRYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class JobStage(str, Enum):
    QUEUED = "queued"
    PARSING = "parsing"
    CLEANING = "cleaning"
    CHUNKING = "chunking"
    GENERATING_EMBEDDINGS = "generating_embeddings"
    INDEXING = "indexing"
    INVALIDATING_CACHE = "invalidating_cache"
    COMPLETED = "completed"


class RetryHistoryItem(BaseModel):
    attempt: int
    timestamp: str
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    delay_seconds: float


class IngestionJobCreate(BaseModel):
    job_id: Optional[str] = None
    tenant_id: str = "default"
    document_id: str
    knowledge_base_id: str
    task_type: str = "document_ingestion"
    priority: int = 5
    max_attempts: int = 3
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IngestionJobResponse(BaseModel):
    id: str
    job_id: str
    tenant_id: str
    document_id: Optional[str] = None
    knowledge_base_id: Optional[str] = None
    document_name: Optional[str] = None
    task_type: str
    status: JobStatus
    priority: int
    progress: int
    current_stage: str
    total_items: int = 0
    processed_items: int = 0
    attempt_count: int = 0
    max_attempts: int = 3
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    worker_id: Optional[str] = None
    queue_wait_time_ms: Optional[float] = None
    processing_time_ms: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    retry_history: List[RetryHistoryItem] = Field(default_factory=list)
    queue_position: Optional[int] = None
    estimated_wait_time_ms: Optional[float] = None
    created_at: str
    started_at: Optional[str] = None
    updated_at: str
    completed_at: Optional[str] = None


class JobListResponse(BaseModel):
    jobs: List[IngestionJobResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class QueueStatsResponse(BaseModel):
    queued: int
    processing: int
    completed_today: int
    failed_today: int
    cancelled_today: int = 0
    active_workers: int
    average_wait_time_ms: float
    average_processing_time_ms: float
    queue_depth: int
    success_rate_pct: float
    retry_rate_pct: float
    worker_utilization_pct: float


class JobRetryRequest(BaseModel):
    reset_attempts: bool = True
    priority: Optional[int] = None


class JobCancelRequest(BaseModel):
    reason: Optional[str] = None


class DocumentUploadAsyncResponse(BaseModel):
    document_id: str
    job_id: str
    status: str = "queued"
    message: str = "Document accepted for background processing"
