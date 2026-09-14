import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Dict, Any
import aiosqlite

from backend.app.core.config import settings
from backend.app.jobs.job_models import (
    JobStatus, JobStage, IngestionJobResponse, QueueStatsResponse, RetryHistoryItem
)
from backend.app.jobs.job_state_machine import JobStateMachine

logger = logging.getLogger("cachemind.jobs.repository")


class JobRepository:
    """
    Asynchronous SQLite repository for ingestion_jobs table.
    Ensures safe concurrent writes, strict state transitions, and metrics querying.
    """

    @staticmethod
    def _row_to_response(row: aiosqlite.Row, doc_name: Optional[str] = None) -> IngestionJobResponse:
        raw_meta = row["metadata"] or "{}"
        try:
            metadata = json.loads(raw_meta)
        except Exception:
            metadata = {}

        retry_history_raw = metadata.get("retry_history", [])
        retry_history = [
            RetryHistoryItem(**item) if isinstance(item, dict) else item
            for item in retry_history_raw
        ]

        # Use document name from join or metadata if available
        document_name = doc_name or metadata.get("original_filename") or metadata.get("filename")

        return IngestionJobResponse(
            id=row["id"],
            job_id=row["job_id"],
            tenant_id=row["tenant_id"],
            document_id=row["document_id"],
            knowledge_base_id=row["knowledge_base_id"],
            document_name=document_name,
            task_type=row["task_type"],
            status=JobStatus(row["status"]),
            priority=row["priority"],
            progress=row["progress"],
            current_stage=row["current_stage"],
            total_items=row["total_items"] or 0,
            processed_items=row["processed_items"] or 0,
            attempt_count=row["attempt_count"] or 0,
            max_attempts=row["max_attempts"] or 3,
            error_code=row["error_code"],
            error_message=row["error_message"],
            worker_id=row["worker_id"],
            queue_wait_time_ms=row["queue_wait_time_ms"],
            processing_time_ms=row["processing_time_ms"],
            metadata=metadata,
            retry_history=retry_history,
            created_at=row["created_at"] or "",
            started_at=row["started_at"],
            updated_at=row["updated_at"] or "",
            completed_at=row["completed_at"]
        )

    async def create_job(
        self,
        document_id: str,
        knowledge_base_id: str,
        job_id: Optional[str] = None,
        tenant_id: str = "default",
        task_type: str = "document_ingestion",
        priority: int = 5,
        max_attempts: int = 3,
        metadata: Optional[Dict[str, Any]] = None
    ) -> IngestionJobResponse:
        pk_id = f"job_pk_{uuid.uuid4().hex[:12]}"
        jid = job_id or f"job_{uuid.uuid4().hex[:12]}"
        meta_json = json.dumps(metadata or {})

        async with aiosqlite.connect(settings.DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            await db.execute(
                """
                INSERT INTO ingestion_jobs (
                    id, job_id, tenant_id, document_id, knowledge_base_id,
                    task_type, status, priority, progress, current_stage,
                    total_items, processed_items, attempt_count, max_attempts,
                    metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pk_id, jid, tenant_id, document_id, knowledge_base_id,
                    task_type, JobStatus.QUEUED.value, priority, 0, JobStage.QUEUED.value,
                    0, 0, 0, max_attempts, meta_json
                )
            )
            await db.commit()

            async with db.execute("SELECT * FROM ingestion_jobs WHERE id = ?", (pk_id,)) as cursor:
                row = await cursor.fetchone()
                return self._row_to_response(row)

    async def get_by_job_id(self, job_id: str) -> Optional[IngestionJobResponse]:
        async with aiosqlite.connect(settings.DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            query = """
                SELECT j.*, d.filename as doc_filename
                FROM ingestion_jobs j
                LEFT JOIN documents d ON j.document_id = d.id
                WHERE j.job_id = ? OR j.id = ?
            """
            async with db.execute(query, (job_id, job_id)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                return self._row_to_response(row, doc_name=row["doc_filename"])

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
    ) -> Tuple[List[IngestionJobResponse], int]:
        clauses = []
        params = []

        if tenant_id:
            clauses.append("j.tenant_id = ?")
            params.append(tenant_id)
        if status:
            clauses.append("j.status = ?")
            params.append(status.upper())
        if task_type:
            clauses.append("j.task_type = ?")
            params.append(task_type)
        if document_id:
            clauses.append("j.document_id = ?")
            params.append(document_id)
        if knowledge_base_id:
            clauses.append("j.knowledge_base_id = ?")
            params.append(knowledge_base_id)
        if created_after:
            clauses.append("j.created_at >= ?")
            params.append(created_after)
        if created_before:
            clauses.append("j.created_at <= ?")
            params.append(created_before)

        where_str = ("WHERE " + " AND ".join(clauses)) if clauses else ""

        offset = max(0, (page - 1) * page_size)

        async with aiosqlite.connect(settings.DB_PATH) as db:
            db.row_factory = aiosqlite.Row

            count_query = f"SELECT COUNT(*) as total FROM ingestion_jobs j {where_str}"
            async with db.execute(count_query, params) as cursor:
                count_row = await cursor.fetchone()
                total = count_row["total"] if count_row else 0

            data_query = f"""
                SELECT j.*, d.filename as doc_filename
                FROM ingestion_jobs j
                LEFT JOIN documents d ON j.document_id = d.id
                {where_str}
                ORDER BY j.created_at DESC
                LIMIT ? OFFSET ?
            """
            async with db.execute(data_query, params + [page_size, offset]) as cursor:
                rows = await cursor.fetchall()
                jobs = [self._row_to_response(r, doc_name=r["doc_filename"]) for r in rows]
                return jobs, total

    async def update_status(
        self,
        job_id: str,
        target_status: JobStatus,
        worker_id: Optional[str] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        is_manual_retry: bool = False
    ) -> IngestionJobResponse:
        async with aiosqlite.connect(settings.DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM ingestion_jobs WHERE job_id = ?", (job_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    raise ValueError(f"Job {job_id} not found.")

            current_status = JobStatus(row["status"])
            JobStateMachine.validate_transition(current_status, target_status, is_manual_retry=is_manual_retry)

            now_iso = datetime.now(timezone.utc).isoformat()
            started_at = row["started_at"]
            completed_at = row["completed_at"]
            wait_time_ms = row["queue_wait_time_ms"]

            if target_status == JobStatus.PROCESSING and not started_at:
                started_at = now_iso
                # Compute queue wait time
                try:
                    created_dt = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
                    wait_time_ms = (datetime.now(timezone.utc) - created_dt).total_seconds() * 1000.0
                except Exception:
                    wait_time_ms = 0.0

            if target_status in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}:
                completed_at = now_iso

            await db.execute(
                """
                UPDATE ingestion_jobs
                SET status = ?,
                    worker_id = COALESCE(?, worker_id),
                    error_code = ?,
                    error_message = ?,
                    started_at = ?,
                    completed_at = ?,
                    queue_wait_time_ms = COALESCE(?, queue_wait_time_ms),
                    updated_at = ?
                WHERE job_id = ?
                """,
                (
                    target_status.value,
                    worker_id,
                    error_code,
                    error_message,
                    started_at,
                    completed_at,
                    wait_time_ms,
                    now_iso,
                    job_id
                )
            )
            await db.commit()

            async with db.execute("SELECT * FROM ingestion_jobs WHERE job_id = ?", (job_id,)) as cursor:
                updated_row = await cursor.fetchone()
                return self._row_to_response(updated_row)

    async def update_progress(
        self,
        job_id: str,
        progress: int,
        current_stage: str,
        processed_items: Optional[int] = None,
        total_items: Optional[int] = None,
        metadata_update: Optional[Dict[str, Any]] = None
    ) -> IngestionJobResponse:
        now_iso = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(settings.DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM ingestion_jobs WHERE job_id = ?", (job_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    raise ValueError(f"Job {job_id} not found.")

            meta = json.loads(row["metadata"] or "{}")
            if metadata_update:
                meta.update(metadata_update)

            await db.execute(
                """
                UPDATE ingestion_jobs
                SET progress = ?,
                    current_stage = ?,
                    processed_items = COALESCE(?, processed_items),
                    total_items = COALESCE(?, total_items),
                    metadata = ?,
                    updated_at = ?
                WHERE job_id = ?
                """,
                (
                    max(0, min(100, progress)),
                    current_stage,
                    processed_items,
                    total_items,
                    json.dumps(meta),
                    now_iso,
                    job_id
                )
            )
            await db.commit()

            async with db.execute("SELECT * FROM ingestion_jobs WHERE job_id = ?", (job_id,)) as cursor:
                updated_row = await cursor.fetchone()
                return self._row_to_response(updated_row)

    async def record_retry_attempt(
        self,
        job_id: str,
        error_code: str,
        error_message: str,
        delay_seconds: float
    ) -> IngestionJobResponse:
        now_iso = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(settings.DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM ingestion_jobs WHERE job_id = ?", (job_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    raise ValueError(f"Job {job_id} not found.")

            new_attempt = (row["attempt_count"] or 0) + 1
            meta = json.loads(row["metadata"] or "{}")
            retry_history = meta.get("retry_history", [])
            retry_history.append({
                "attempt": new_attempt,
                "timestamp": now_iso,
                "error_code": error_code,
                "error_message": error_message,
                "delay_seconds": round(delay_seconds, 2)
            })
            meta["retry_history"] = retry_history

            await db.execute(
                """
                UPDATE ingestion_jobs
                SET attempt_count = ?,
                    status = ?,
                    current_stage = ?,
                    error_code = ?,
                    error_message = ?,
                    metadata = ?,
                    updated_at = ?
                WHERE job_id = ?
                """,
                (
                    new_attempt,
                    JobStatus.RETRYING.value,
                    "retrying",
                    error_code,
                    error_message,
                    json.dumps(meta),
                    now_iso,
                    job_id
                )
            )
            await db.commit()

            async with db.execute("SELECT * FROM ingestion_jobs WHERE job_id = ?", (job_id,)) as cursor:
                updated_row = await cursor.fetchone()
                return self._row_to_response(updated_row)

    async def mark_completed(
        self,
        job_id: str,
        processing_time_ms: float,
        metadata_update: Optional[Dict[str, Any]] = None
    ) -> IngestionJobResponse:
        now_iso = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(settings.DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM ingestion_jobs WHERE job_id = ?", (job_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    raise ValueError(f"Job {job_id} not found.")

            current_status = JobStatus(row["status"])
            JobStateMachine.validate_transition(current_status, JobStatus.COMPLETED)

            meta = json.loads(row["metadata"] or "{}")
            if metadata_update:
                meta.update(metadata_update)

            await db.execute(
                """
                UPDATE ingestion_jobs
                SET status = ?,
                    progress = 100,
                    current_stage = ?,
                    completed_at = ?,
                    processing_time_ms = ?,
                    metadata = ?,
                    updated_at = ?
                WHERE job_id = ?
                """,
                (
                    JobStatus.COMPLETED.value,
                    JobStage.COMPLETED.value,
                    now_iso,
                    round(processing_time_ms, 2),
                    json.dumps(meta),
                    now_iso,
                    job_id
                )
            )
            await db.commit()

            async with db.execute("SELECT * FROM ingestion_jobs WHERE job_id = ?", (job_id,)) as cursor:
                updated_row = await cursor.fetchone()
                return self._row_to_response(updated_row)

    async def get_queue_position(self, job_id: str) -> Tuple[int, float]:
        """
        Calculates 1-based queue position and estimated wait time based on avg processing duration.
        """
        async with aiosqlite.connect(settings.DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM ingestion_jobs WHERE job_id = ?", (job_id,)) as cursor:
                target = await cursor.fetchone()
                if not target or target["status"] != JobStatus.QUEUED.value:
                    return 0, 0.0

            # Count queued jobs created before this one
            count_query = """
                SELECT COUNT(*) as pos
                FROM ingestion_jobs
                WHERE status = 'QUEUED'
                  AND (created_at < ? OR (created_at = ? AND id <= ?))
            """
            async with db.execute(count_query, (target["created_at"], target["created_at"], target["id"])) as cursor:
                row = await cursor.fetchone()
                position = row["pos"] if row else 1

            # Estimate based on recent average processing time
            avg_query = "SELECT AVG(processing_time_ms) as avg_time FROM ingestion_jobs WHERE status = 'COMPLETED' AND processing_time_ms IS NOT NULL"
            async with db.execute(avg_query) as cursor:
                avg_row = await cursor.fetchone()
                avg_ms = avg_row["avg_time"] if avg_row and avg_row["avg_time"] else 3000.0

            estimated_wait = position * avg_ms
            return position, round(estimated_wait, 2)

    async def get_queue_stats(self, tenant_id: str = "default") -> QueueStatsResponse:
        today_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        async with aiosqlite.connect(settings.DB_PATH) as db:
            db.row_factory = aiosqlite.Row

            query = """
                SELECT
                    SUM(CASE WHEN status = 'QUEUED' THEN 1 ELSE 0 END) as queued_count,
                    SUM(CASE WHEN status = 'PROCESSING' THEN 1 ELSE 0 END) as processing_count,
                    SUM(CASE WHEN status = 'COMPLETED' AND date(completed_at) >= date(?) THEN 1 ELSE 0 END) as completed_today,
                    SUM(CASE WHEN status = 'FAILED' AND date(completed_at) >= date(?) THEN 1 ELSE 0 END) as failed_today,
                    SUM(CASE WHEN status = 'CANCELLED' AND date(updated_at) >= date(?) THEN 1 ELSE 0 END) as cancelled_today,
                    COUNT(DISTINCT CASE WHEN status = 'PROCESSING' AND worker_id IS NOT NULL THEN worker_id END) as active_workers,
                    AVG(queue_wait_time_ms) as avg_wait,
                    AVG(processing_time_ms) as avg_proc,
                    SUM(CASE WHEN attempt_count > 0 THEN 1 ELSE 0 END) as retried_count,
                    COUNT(*) as total_count
                FROM ingestion_jobs
                WHERE tenant_id = ?
            """
            async with db.execute(query, (today_iso, today_iso, today_iso, tenant_id)) as cursor:
                row = await cursor.fetchone()

                queued = row["queued_count"] or 0
                processing = row["processing_count"] or 0
                completed_today = row["completed_today"] or 0
                failed_today = row["failed_today"] or 0
                cancelled_today = row["cancelled_today"] or 0
                active_workers = max(1 if processing > 0 else 0, row["active_workers"] or 0)
                avg_wait = round(row["avg_wait"] or 0.0, 2)
                avg_proc = round(row["avg_proc"] or 0.0, 2)
                retried = row["retried_count"] or 0
                total = row["total_count"] or 0

                total_finished = completed_today + failed_today
                success_rate = (completed_today / total_finished * 100.0) if total_finished > 0 else 100.0
                retry_rate = (retried / total * 100.0) if total > 0 else 0.0
                worker_utilization = min(100.0, (processing / max(1, active_workers)) * 100.0)

                return QueueStatsResponse(
                    queued=queued,
                    processing=processing,
                    completed_today=completed_today,
                    failed_today=failed_today,
                    cancelled_today=cancelled_today,
                    active_workers=active_workers,
                    average_wait_time_ms=avg_wait,
                    average_processing_time_ms=avg_proc,
                    queue_depth=queued + processing,
                    success_rate_pct=round(success_rate, 1),
                    retry_rate_pct=round(retry_rate, 1),
                    worker_utilization_pct=round(worker_utilization, 1)
                )


job_repository = JobRepository()
