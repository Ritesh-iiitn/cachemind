import shutil
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from backend.app.models.schemas import (
    KnowledgeBaseCreate, KnowledgeBaseResponse, DocumentResponse
)
from backend.app.ingestion.service import ingestion_service
from backend.app.cache.invalidation import invalidator
from backend.app.core.config import settings

router = APIRouter()

@router.post("", response_model=KnowledgeBaseResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(payload: KnowledgeBaseCreate):
    return await ingestion_service.create_knowledge_base(payload.name, payload.description)

@router.get("", response_model=List[KnowledgeBaseResponse])
async def list_knowledge_bases():
    return await ingestion_service.list_knowledge_bases()

@router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(kb_id: str):
    kb = await ingestion_service.get_kb(kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found.")
    return kb

@router.post("/{kb_id}/documents", response_model=DocumentResponse)
async def upload_document(
    kb_id: str,
    file: UploadFile = File(...)
):
    kb = await ingestion_service.get_kb(kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found.")

    # Save temp upload
    kb_dir = settings.DOCUMENT_STORAGE / kb_id
    kb_dir.mkdir(parents=True, exist_ok=True)
    temp_path = kb_dir / file.filename

    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        doc = await ingestion_service.index_document(
            kb_id=kb_id,
            file_path=temp_path,
            original_filename=file.filename
        )
        # Automatic multi-tier cache invalidation on doc addition
        invalidator.invalidate_knowledge_base(kb_id)
        return doc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process and index document: {str(e)}")

@router.get("/{kb_id}/documents", response_model=List[DocumentResponse])
async def list_documents(kb_id: str):
    return await ingestion_service.list_documents(kb_id)

@router.delete("/{kb_id}/documents/{doc_id}")
async def delete_document(kb_id: str, doc_id: str):
    deleted = await ingestion_service.delete_document(kb_id, doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found.")
    invalidator.invalidate_knowledge_base(kb_id)
    return {"status": "success", "message": f"Document {doc_id} deleted and cache invalidated."}
