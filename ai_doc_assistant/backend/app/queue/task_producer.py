import logging
from typing import Dict, Any, Optional

from backend.app.jobs.job_repository import job_repository
from backend.app.jobs.job_models import IngestionJobResponse, JobStatus
from backend.app.queue.queue_manager import queue_manager
from backend.app.queue.task_events import event_broadcaster

logger = logging.getLogger("cachemind.queue.producer")


class TaskProducer:
    """
    Producer facade for creating ingestion jobs and dispatching them to the Redis queue.
    Ensures transactional persistence before queue delivery.
    """

    @classmethod
    async def submit_ingestion_task(
        cls,
        document_id: str,
        knowledge_base_id: str,
        job_id: Optional[str] = None,
        tenant_id: str = "default",
        priority: int = 5,
        max_attempts: int = 3,
        metadata: Optional[Dict[str, Any]] = None
    ) -> IngestionJobResponse:
        # 1. Persist Job in database with status QUEUED
        job = await job_repository.create_job(
            document_id=document_id,
            knowledge_base_id=knowledge_base_id,
            job_id=job_id,
            tenant_id=tenant_id,
            task_type="document_ingestion",
            priority=priority,
            max_attempts=max_attempts,
            metadata=metadata
        )

        # 2. Push to Redis Queue Broker
        await queue_manager.enqueue(
            job_id=job.job_id,
            priority=priority,
            delay_seconds=0.0,
            metadata={"document_id": document_id, "knowledge_base_id": knowledge_base_id}
        )

        # 3. Emit real-time event to subscribers
        await event_broadcaster.emit_event(
            event_type="job_created",
            job_id=job.job_id,
            data=job.model_dump()
        )

        logger.info(f"TaskProducer: Enqueued ingestion job {job.job_id} for doc {document_id}")
        return job


task_producer = TaskProducer()
