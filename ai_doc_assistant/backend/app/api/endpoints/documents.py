import uuid
import shutil
import hashlib
import logging
from pathlib import Path
from typing import Optional
import aiosqlite
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status

from backend.app.core.config import settings
from backend.app.jobs.job_models import DocumentUploadAsyncResponse
from backend.app.queue.task_producer import task_producer

logger = logging.getLogger("cachemind.api.documents")

router = APIRouter()

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown", ".docx", ".csv", ".json"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def compute_sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


@router.post(
    "/upload",
    response_model=DocumentUploadAsyncResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Asynchronous Document Upload & Ingestion Enqueue"
)
async def upload_document_async(
    file: UploadFile = File(...),
    knowledge_base_id: Optional[str] = Form(None),
    kb_id: Optional[str] = Form(None),
    tenant_id: str = Form("default"),
    priority: int = Form(5)
):
    """
    Accepts document file, validates size and format, stores file safely,
    creates persistent document and job records, enqueues ingestion to Redis,
    and returns immediately (<50ms).
    """
    target_kb_id = knowledge_base_id or kb_id

    # 1. Validate knowledge base
    if not target_kb_id:
        # Check if there is an existing KB, or fetch the first default KB
        async with aiosqlite.connect(settings.DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT id FROM knowledge_bases ORDER BY created_at ASC LIMIT 1") as cursor:
                first_kb = await cursor.fetchone()
                if first_kb:
                    target_kb_id = first_kb["id"]
                else:
                    raise HTTPException(
                        status_code=400,
                        detail="knowledge_base_id is required. Create a Knowledge Base first."
                    )
    else:
        async with aiosqlite.connect(settings.DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT id FROM knowledge_bases WHERE id = ?", (target_kb_id,)) as cursor:
                exists = await cursor.fetchone()
                if not exists:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Knowledge Base {target_kb_id} does not exist."
                    )

    # 2. Validate file type & name
    filename = file.filename or "uploaded_doc"
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed extensions: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    # 3. Save uploaded file safely to disk
    kb_dir = settings.DOCUMENT_STORAGE / target_kb_id
    kb_dir.mkdir(parents=True, exist_ok=True)
    temp_path = kb_dir / filename

    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        raise HTTPException(status_code=500, detail="Failed to store uploaded file.")

    file_size = temp_path.stat().st_size
    if file_size > MAX_FILE_SIZE:
        temp_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size limit of {MAX_FILE_SIZE // (1024*1024)}MB"
        )

    content_hash = compute_sha256(temp_path)
    document_id = f"doc_{uuid.uuid4().hex[:10]}"
    file_type = ext.lstrip(".") or "txt"

    # 4. Persist Document metadata in SQLite
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO documents (
                id, kb_id, filename, file_type, file_size, version,
                status, chunk_count, content_hash
            ) VALUES (?, ?, ?, ?, ?, 1, 'queued', 0, ?)
            """,
            (document_id, target_kb_id, filename, file_type, file_size, content_hash)
        )
        await db.commit()

    # 5. Create Ingestion Job and Enqueue to Redis Queue
    job_id = f"job_{uuid.uuid4().hex[:10]}"
    job = await task_producer.submit_ingestion_task(
        document_id=document_id,
        knowledge_base_id=target_kb_id,
        job_id=job_id,
        tenant_id=tenant_id,
        priority=priority,
        metadata={
            "filename": filename,
            "file_size": file_size,
            "content_hash": content_hash,
            "file_type": file_type
        }
    )

    logger.info(f"Accepted document '{filename}' (doc_id={document_id}) with job {job.job_id}")

    return DocumentUploadAsyncResponse(
        document_id=document_id,
        job_id=job.job_id,
        status="queued",
        message="Document accepted for background processing"
    )
