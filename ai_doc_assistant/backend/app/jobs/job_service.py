import logging
from typing import Optional, List, Dict, Any

from backend.app.jobs.job_models import (
    IngestionJobResponse, JobListResponse, QueueStatsResponse, JobStatus
)
from backend.app.jobs.job_repository import job_repository
from backend.app.queue.queue_manager import queue_manager
from backend.app.queue.task_events import event_broadcaster

logger = logging.getLogger("cachemind.jobs.service")


class JobService:
    """
    High-level domain service orchestrating job tracking, cancellation,
    manual recovery retries, and queue performance telemetry.
    """

    async def get_job(self, job_id: str) -> Optional[IngestionJobResponse]:
        job = await job_repository.get_by_job_id(job_id)
        if not job:
            return None

        # If queued, calculate estimated queue position and wait time
        if job.status == JobStatus.QUEUED:
            pos, est_wait = await job_repository.get_queue_position(job.job_id)
            job.queue_position = pos
            job.estimated_wait_time_ms = est_wait

        return job

    async def list_jobs(
        self,
        tenant_id: Optional[str] = None,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        document_id: Optional[str] = None,
        knowledge_base_id: Optional[str] = None,
        created_after: Optional[str] = None,
        created_before: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> JobListResponse:
        jobs, total = await job_repository.list_jobs(
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
        total_pages = max(1, (total + page_size - 1) // page_size) if total > 0 else 1
        return JobListResponse(
            jobs=jobs,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    async def get_queue_stats(self, tenant_id: str = "default") -> QueueStatsResponse:
        stats = await job_repository.get_queue_stats(tenant_id)
        # Augment with live worker heartbeat and redis queue depth
        real_workers = await queue_manager.get_active_worker_count()
        if real_workers > stats.active_workers:
            stats.active_workers = real_workers
        depth = await queue_manager.get_queue_depth()
        if depth > stats.queue_depth:
            stats.queue_depth = depth
        return stats

    async def cancel_job(self, job_id: str, reason: Optional[str] = None) -> IngestionJobResponse:
        job = await job_repository.get_by_job_id(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found.")

        if job.status in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}:
            raise ValueError(f"Cannot cancel job in terminal state: {job.status.value}")

        updated_job = await job_repository.update_status(
            job_id=job.job_id,
            target_status=JobStatus.CANCELLED,
            error_code="CANCELLED_BY_USER",
            error_message=reason or "Task cancelled by user request"
        )
        await queue_manager.ack(job.job_id)

        await event_broadcaster.emit_event(
            event_type="job_cancelled",
            job_id=job.job_id,
            data={"reason": reason}
        )
        return updated_job

    async def retry_job(
        self,
        job_id: str,
        reset_attempts: bool = True,
        priority: Optional[int] = None
    ) -> IngestionJobResponse:
        job = await job_repository.get_by_job_id(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found.")

        if job.status not in {JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.RETRYING}:
            raise ValueError(f"Only FAILED, CANCELLED, or RETRYING jobs can be retried. Current state: {job.status.value}")

        # Re-transition to QUEUED via manual retry
        updated_job = await job_repository.update_status(
            job_id=job.job_id,
            target_status=JobStatus.QUEUED,
            is_manual_retry=True
        )

        # Reset progress to 0 and current_stage to queued
        target_priority = priority if priority is not None else job.priority
        await job_repository.update_progress(
            job_id=job.job_id,
            progress=0,
            current_stage="queued"
        )

        # Re-enqueue into priority queue
        await queue_manager.enqueue(
            job_id=job.job_id,
            priority=target_priority,
            delay_seconds=0.0
        )

        # Emit retry event
        await event_broadcaster.emit_event(
            event_type="job_retried",
            job_id=job.job_id,
            data={"manual": True, "priority": target_priority}
        )
        return updated_job


job_service = JobService()
