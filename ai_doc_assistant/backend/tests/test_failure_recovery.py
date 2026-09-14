import pytest
import aiosqlite

from backend.app.core.config import settings
from backend.app.core.database import init_db
from backend.app.jobs.job_repository import job_repository
from backend.app.jobs.job_service import job_service
from backend.app.jobs.job_models import JobStatus
from backend.app.queue.queue_manager import queue_manager
from backend.app.queue.task_producer import task_producer
from backend.app.workers.ingestion_tasks import ingestion_task_executor


@pytest.mark.anyio
async def test_permanent_failure_transitions_to_failed_without_retry():
    await init_db()
    await queue_manager.clear_all()

    kb_id = "kb_fail_test"
    doc_id = "doc_missing_test"

    # Insert Document pointing to non-existent file
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO knowledge_bases (id, name, version) VALUES (?, ?, ?)", (kb_id, "Fail KB", 1))
        await db.execute(
            """
            INSERT OR REPLACE INTO documents (id, kb_id, filename, file_type, file_size, version, status, chunk_count, content_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (doc_id, kb_id, "non_existent_file.pdf", "pdf", 100, 1, "queued", 0, "hash_missing")
        )
        await db.commit()

    # Enqueue job
    job = await task_producer.submit_ingestion_task(
        document_id=doc_id,
        knowledge_base_id=kb_id,
        metadata={"filename": "non_existent_file.pdf"}
    )

    # Worker executes job with missing file
    await ingestion_task_executor.execute_job(job_id=job.job_id, worker_id="worker_fail_test")

    # Verify job failed permanently
    failed_job = await job_repository.get_by_job_id(job.job_id)
    assert failed_job is not None
    assert failed_job.status == JobStatus.FAILED
    assert "PERMANENT" in (failed_job.error_code or "")


@pytest.mark.anyio
async def test_manual_retry_resurrects_failed_job():
    await init_db()
    await queue_manager.clear_all()

    kb_id = "kb_resurrect_test"
    doc_id = "doc_resurrect_test"

    job = await job_repository.create_job(
        document_id=doc_id,
        knowledge_base_id=kb_id,
        metadata={"filename": "doc.pdf"}
    )

    # Manually fail job
    await job_repository.update_status(
        job_id=job.job_id,
        target_status=JobStatus.PROCESSING
    )
    await job_repository.update_status(
        job_id=job.job_id,
        target_status=JobStatus.FAILED,
        error_code="TEST_ERROR",
        error_message="Simulated temporary error"
    )

    # Perform manual retry
    retried_job = await job_service.retry_job(job.job_id, reset_attempts=True, priority=9)

    assert retried_job.status == JobStatus.QUEUED
    assert retried_job.progress == 0
    assert retried_job.current_stage == "queued"

    # Verify task was placed back into high-priority Redis queue
    depth = await queue_manager.get_queue_depth()
    assert depth >= 1


@pytest.mark.anyio
async def test_duplicate_task_delivery_is_safe():
    await init_db()

    kb_id = "kb_dup_test"
    doc_id = "doc_dup_test"

    job = await job_repository.create_job(
        document_id=doc_id,
        knowledge_base_id=kb_id,
        metadata={"filename": "doc.pdf"}
    )

    # Mark as COMPLETED
    await job_repository.update_status(job.job_id, JobStatus.PROCESSING)
    await job_repository.mark_completed(job.job_id, processing_time_ms=150.0)

    # Deliver duplicate task to worker
    await ingestion_task_executor.execute_job(job_id=job.job_id, worker_id="worker_dup")

    # Verify status remains COMPLETED and was not mutated or re-executed
    job_after = await job_repository.get_by_job_id(job.job_id)
    assert job_after.status == JobStatus.COMPLETED
    assert job_after.processing_time_ms == 150.0
