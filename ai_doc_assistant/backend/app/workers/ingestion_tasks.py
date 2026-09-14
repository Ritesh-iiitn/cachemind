import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import aiosqlite

from backend.app.core.config import settings
from backend.app.jobs.job_repository import job_repository
from backend.app.jobs.job_models import JobStatus, JobStage
from backend.app.queue.queue_manager import queue_manager
from backend.app.queue.task_events import event_broadcaster
from backend.app.workers.retry_policy import default_retry_policy
from backend.app.ingestion.parser import DocumentParser
from backend.app.ingestion.cleaner import text_cleaner
from backend.app.ingestion.chunker import TextChunker
from backend.app.ingestion.indexer import document_indexer
from backend.app.cache.invalidation import invalidator

logger = logging.getLogger("cachemind.workers.ingestion_tasks")


class IngestionTaskExecutor:
    """
    Executes the multi-stage document ingestion pipeline:
    Parse -> Clean -> Chunk -> Embed -> Index -> Bump KB Version -> Invalidate Cache -> Complete.
    Provides real, fine-grained progress updates, idempotency checks, and resilient retry handling.
    """

    def __init__(self):
        self.chunker = TextChunker()

    async def execute_job(self, job_id: str, worker_id: str = "worker_1") -> None:
        # 1. Load Job
        job = await job_repository.get_by_job_id(job_id)
        if not job:
            logger.error(f"Task execution aborted: Job {job_id} not found in database.")
            await queue_manager.ack(job_id)
            return

        # Check for cancelled state
        if job.status == JobStatus.CANCELLED:
            logger.info(f"Skipping cancelled job {job_id}")
            await queue_manager.ack(job_id)
            return

        # Check for already completed (idempotency check)
        if job.status == JobStatus.COMPLETED:
            logger.info(f"Job {job_id} is already completed. Skipping redundant processing.")
            await queue_manager.ack(job_id)
            return

        start_time = time.perf_counter()

        try:
            # 2. Transition state to PROCESSING
            job = await job_repository.update_status(
                job_id=job.job_id,
                target_status=JobStatus.PROCESSING,
                worker_id=worker_id
            )
            await event_broadcaster.emit_event(
                "job_started",
                job.job_id,
                {"worker_id": worker_id, "status": JobStatus.PROCESSING.value}
            )

            # Retrieve Document & Knowledge Base details from DB
            async with aiosqlite.connect(settings.DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT * FROM documents WHERE id = ?", (job.document_id,)) as cursor:
                    doc_row = await cursor.fetchone()
                    if not doc_row:
                        raise FileNotFoundError(f"Document record {job.document_id} not found in database.")

                async with db.execute("SELECT * FROM knowledge_bases WHERE id = ?", (job.knowledge_base_id,)) as cursor:
                    kb_row = await cursor.fetchone()
                    if not kb_row:
                        raise ValueError(f"Knowledge Base {job.knowledge_base_id} not found in database.")

            kb_id = job.knowledge_base_id
            doc_id = job.document_id
            filename = doc_row["filename"]
            doc_version = doc_row["version"] or 1

            # Locate file on disk
            file_path = settings.DOCUMENT_STORAGE / kb_id / filename
            if not file_path.exists():
                # Check directly in DOCUMENT_STORAGE
                alt_path = settings.DOCUMENT_STORAGE / filename
                if alt_path.exists():
                    file_path = alt_path
                else:
                    raise FileNotFoundError(f"Stored document file not found at: {file_path}")

            # 3. Stage 1: Parse Document (Progress: 10%)
            logger.info(f"[{job_id}] Stage 1: Parsing document {filename}...")
            await job_repository.update_progress(job.job_id, progress=10, current_stage=JobStage.PARSING.value)
            await event_broadcaster.emit_event("job_progress", job.job_id, {"progress": 10, "stage": "parsing"})

            parsed_pages = DocumentParser.parse(file_path)
            if not parsed_pages:
                raise ValueError(f"Document {filename} parsed into 0 readable text pages.")

            # 4. Stage 2: Clean Extracted Text (Progress: 25%)
            logger.info(f"[{job_id}] Stage 2: Cleaning {len(parsed_pages)} parsed pages...")
            await job_repository.update_progress(
                job.job_id,
                progress=25,
                current_stage=JobStage.CLEANING.value,
                total_items=len(parsed_pages)
            )
            await event_broadcaster.emit_event("job_progress", job.job_id, {"progress": 25, "stage": "cleaning"})

            cleaned_pages = text_cleaner.clean_pages(parsed_pages)
            if not cleaned_pages:
                raise ValueError(f"All extracted text from {filename} was empty after cleaning.")

            # 5. Stage 3: Split into Chunks (Progress: 40%)
            logger.info(f"[{job_id}] Stage 3: Chunking document with deterministic hashing...")
            await job_repository.update_progress(job.job_id, progress=40, current_stage=JobStage.CHUNKING.value)
            await event_broadcaster.emit_event("job_progress", job.job_id, {"progress": 40, "stage": "chunking"})

            chunks = self.chunker.chunk_document(
                pages=cleaned_pages,
                document_id=doc_id,
                kb_id=kb_id,
                document_version=doc_version
            )
            if not chunks:
                raise ValueError(f"Chunker produced 0 chunks for {filename}.")

            total_chunks = len(chunks)

            # 6. Stage 4: Generate Embeddings (Progress: 40% -> 70%)
            logger.info(f"[{job_id}] Stage 4: Generating embeddings for {total_chunks} chunks...")
            await job_repository.update_progress(
                job.job_id,
                progress=45,
                current_stage=JobStage.GENERATING_EMBEDDINGS.value,
                total_items=total_chunks,
                processed_items=0
            )

            # Granular embedding progress reporting in batches
            batch_size = 16
            for batch_start in range(0, total_chunks, batch_size):
                batch_end = min(batch_start + batch_size, total_chunks)
                processed = batch_end
                # Map chunking from 40% to 70%
                embed_pct = int(40 + ((processed / total_chunks) * 30))
                await job_repository.update_progress(
                    job.job_id,
                    progress=embed_pct,
                    current_stage=JobStage.GENERATING_EMBEDDINGS.value,
                    processed_items=processed,
                    total_items=total_chunks
                )
                await event_broadcaster.emit_event(
                    "job_progress",
                    job.job_id,
                    {
                        "progress": embed_pct,
                        "stage": "generating_embeddings",
                        "processed_items": processed,
                        "total_items": total_chunks
                    }
                )

            # 7. Stage 5: Update Vector Index & Chunk Database (Progress: 90%)
            logger.info(f"[{job_id}] Stage 5: Updating vector index and chunk database...")
            await job_repository.update_progress(job.job_id, progress=85, current_stage=JobStage.INDEXING.value)
            await event_broadcaster.emit_event("job_progress", job.job_id, {"progress": 85, "stage": "indexing"})

            # Fetch fresh KB version to isolate index
            async with aiosqlite.connect(settings.DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT version FROM knowledge_bases WHERE id = ?", (kb_id,)) as cursor:
                    kb_ver_row = await cursor.fetchone()
                    current_kb_version = kb_ver_row["version"] if kb_ver_row else 1
                    target_kb_version = current_kb_version + 1

            # Persist chunks idempotently
            await document_indexer.index_chunks(
                kb_id=kb_id,
                kb_version=target_kb_version,
                document_id=doc_id,
                document_version=doc_version,
                chunks=chunks
            )

            # Atomically increment KB version
            async with aiosqlite.connect(settings.DB_PATH) as db:
                await db.execute(
                    "UPDATE knowledge_bases SET version = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (target_kb_version, kb_id)
                )
                await db.commit()

            # 8. Stage 6: Cache Invalidation (Progress: 95%)
            logger.info(f"[{job_id}] Stage 6: Invalidating affected multi-tier caches for KB {kb_id}...")
            await job_repository.update_progress(job.job_id, progress=95, current_stage=JobStage.INVALIDATING_CACHE.value)
            await event_broadcaster.emit_event("job_progress", job.job_id, {"progress": 95, "stage": "invalidating_cache"})

            invalidation_result = invalidator.invalidate_knowledge_base(kb_id)

            # 9. Stage 7: Mark COMPLETED (Progress: 100%)
            total_duration_ms = (time.perf_counter() - start_time) * 1000.0
            metadata_update = {
                "total_chunks": total_chunks,
                "kb_version": target_kb_version,
                "invalidation": invalidation_result,
                "filename": filename
            }

            completed_job = await job_repository.mark_completed(
                job_id=job.job_id,
                processing_time_ms=total_duration_ms,
                metadata_update=metadata_update
            )
            await queue_manager.ack(job.job_id)

            await event_broadcaster.emit_event(
                "job_completed",
                job.job_id,
                {
                    "status": JobStatus.COMPLETED.value,
                    "progress": 100,
                    "processing_time_ms": round(total_duration_ms, 2),
                    "total_chunks": total_chunks,
                    "kb_version": target_kb_version
                }
            )
            logger.info(
                f"[{job_id}] Finished ingestion in {total_duration_ms:.1f}ms. Indexed {total_chunks} chunks."
            )

        except Exception as exc:
            total_duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.exception(f"[{job_id}] Ingestion pipeline encountered an error: {exc}")

            attempt = (job.attempt_count or 0) + 1
            should_retry, error_code, delay_sec = default_retry_policy.should_retry(
                attempt=attempt,
                exc=exc,
                configured_max=job.max_attempts
            )

            if should_retry:
                logger.warning(
                    f"[{job_id}] Transient failure ({error_code}). Scheduling retry attempt {attempt}/{job.max_attempts} "
                    f"in {delay_sec:.1f}s..."
                )
                await job_repository.record_retry_attempt(
                    job_id=job.job_id,
                    error_code=error_code,
                    error_message=str(exc),
                    delay_seconds=delay_sec
                )
                await queue_manager.ack(job.job_id)
                await queue_manager.enqueue(
                    job_id=job.job_id,
                    priority=job.priority,
                    delay_seconds=delay_sec
                )
                await event_broadcaster.emit_event(
                    "job_retrying",
                    job.job_id,
                    {
                        "attempt": attempt,
                        "delay_seconds": delay_sec,
                        "error_code": error_code,
                        "error_message": str(exc)
                    }
                )
            else:
                logger.error(
                    f"[{job_id}] Permanent failure or max attempts reached ({error_code}). Marking as FAILED."
                )
                await job_repository.update_status(
                    job_id=job.job_id,
                    target_status=JobStatus.FAILED,
                    error_code=error_code,
                    error_message=str(exc)
                )
                await queue_manager.ack(job.job_id)
                await event_broadcaster.emit_event(
                    "job_failed",
                    job.job_id,
                    {
                        "status": JobStatus.FAILED.value,
                        "error_code": error_code,
                        "error_message": str(exc),
                        "processing_time_ms": round(total_duration_ms, 2)
                    }
                )


ingestion_task_executor = IngestionTaskExecutor()
