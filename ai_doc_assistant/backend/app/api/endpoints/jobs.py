import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from backend.app.jobs.job_models import (
    IngestionJobResponse, JobListResponse, QueueStatsResponse,
    JobRetryRequest, JobCancelRequest
)
from backend.app.jobs.job_service import job_service

logger = logging.getLogger("cachemind.api.jobs")

router = APIRouter()


@router.get("", response_model=JobListResponse, summary="List ingestion jobs with filtering and pagination")
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by status: QUEUED, PROCESSING, RETRYING, COMPLETED, FAILED, CANCELLED"),
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    document_id: Optional[str] = Query(None, description="Filter by document ID"),
    knowledge_base_id: Optional[str] = Query(None, description="Filter by knowledge base ID"),
    created_after: Optional[str] = Query(None, description="ISO timestamp filter"),
    created_before: Optional[str] = Query(None, description="ISO timestamp filter"),
    tenant_id: str = Query("default", description="Tenant ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size")
):
    return await job_service.list_jobs(
        tenant_id=tenant_id,
        status=status,
        task_type=task_type,
        document_id=document_id,
        knowledge_base_id=knowledge_base_id,
        created_after=created_after,
        created_before=created_before,
        page=page,
        page_size=page_size
    )


queue_router = APIRouter()

@queue_router.get("/stats", response_model=QueueStatsResponse, summary="Get real-time queue metrics and worker telemetry")
async def get_queue_stats_alt(tenant_id: str = Query("default")):
    return await job_service.get_queue_stats(tenant_id=tenant_id)


@router.get("/stats", response_model=QueueStatsResponse, summary="Get real-time queue metrics and worker telemetry")
async def get_queue_stats(tenant_id: str = Query("default")):
    return await job_service.get_queue_stats(tenant_id=tenant_id)



@router.get("/{job_id}", response_model=IngestionJobResponse, summary="Get detailed job status by ID")
async def get_job(job_id: str):
    job = await job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return job


@router.post("/{job_id}/cancel", response_model=IngestionJobResponse, summary="Cancel an active or queued job")
async def cancel_job(job_id: str, payload: Optional[JobCancelRequest] = None):
    reason = payload.reason if payload else "User requested cancellation"
    try:
        return await job_service.cancel_job(job_id, reason=reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{job_id}/retry", response_model=IngestionJobResponse, summary="Manually retry a failed or cancelled job")
async def retry_job(job_id: str, payload: Optional[JobRetryRequest] = None):
    reset_attempts = payload.reset_attempts if payload else True
    priority = payload.priority if payload else None
    try:
        return await job_service.retry_job(job_id, reset_attempts=reset_attempts, priority=priority)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
