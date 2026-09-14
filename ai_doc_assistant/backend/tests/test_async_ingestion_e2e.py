import pytest
import asyncio
from pathlib import Path
import aiosqlite

from backend.app.core.config import settings
from backend.app.core.database import init_db
from backend.app.jobs.job_repository import job_repository
from backend.app.jobs.job_models import JobStatus
from backend.app.queue.queue_manager import queue_manager
from backend.app.queue.task_producer import task_producer
from backend.app.queue.task_events import event_broadcaster
from backend.app.workers.ingestion_tasks import ingestion_task_executor


@pytest.mark.anyio
async def test_full_async_ingestion_pipeline_e2e(tmp_path):
    await init_db()
    await queue_manager.clear_all()

    kb_id = "kb_e2e_test"
    doc_id = "doc_e2e_test"
    filename = "sample_architecture.txt"

    # 1. Setup sample document file on disk
    doc_dir = settings.DOCUMENT_STORAGE / kb_id
    doc_dir.mkdir(parents=True, exist_ok=True)
    file_path = doc_dir / filename
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("# Distributed Queue Architecture\n\nRedis backed queues ensure task durability and decouples ingestion.\n\nWorkers consume jobs and write embeddings asynchronously.")

    # 2. Insert Knowledge Base and Document records
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO knowledge_bases (id, name, version) VALUES (?, ?, ?)", (kb_id, "E2E Test KB", 1))
        await db.execute(
            """
            INSERT OR REPLACE INTO documents (id, kb_id, filename, file_type, file_size, version, status, chunk_count, content_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (doc_id, kb_id, filename, "txt", file_path.stat().st_size, 1, "queued", 0, "hash_e2e")
        )
        await db.commit()

    # 3. Subscribe to real-time events
    event_queue = event_broadcaster.subscribe()

    # 4. Enqueue Ingestion Job via Producer
    job = await task_producer.submit_ingestion_task(
        document_id=doc_id,
        knowledge_base_id=kb_id,
        priority=8,
        metadata={"filename": filename}
    )

    assert job.status == JobStatus.QUEUED
    assert job.job_id.startswith("job_")

    # Verify event emitted
    event1 = await asyncio.wait_for(event_queue.get(), timeout=2.0)
    assert event1["event_type"] == "job_created"

    # 5. Check Queue Depth
    depth = await queue_manager.get_queue_depth()
    assert depth >= 1

    # 6. Dequeue task
    task_data = await queue_manager.dequeue(timeout_seconds=1.0)
    assert task_data is not None
    assert task_data["job_id"] == job.job_id

    # 7. Execute Ingestion Task via Worker Pipeline
    await ingestion_task_executor.execute_job(job_id=job.job_id, worker_id="test_worker_e2e")

    # 8. Verify Job Status is COMPLETED
    completed_job = await job_repository.get_by_job_id(job.job_id)
    assert completed_job is not None
    assert completed_job.status == JobStatus.COMPLETED
    assert completed_job.progress == 100
    assert completed_job.current_stage == "completed"
    assert completed_job.processing_time_ms is not None
    assert completed_job.processing_time_ms > 0

    # 9. Verify KB version was bumped
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT version FROM knowledge_bases WHERE id = ?", (kb_id,)) as cursor:
            kb_row = await cursor.fetchone()
            assert kb_row["version"] == 2

        # Verify chunks exist
        async with db.execute("SELECT COUNT(*) as cnt FROM document_chunks WHERE document_id = ?", (doc_id,)) as cursor:
            cnt_row = await cursor.fetchone()
            assert cnt_row["cnt"] > 0

    event_broadcaster.unsubscribe(event_queue)
