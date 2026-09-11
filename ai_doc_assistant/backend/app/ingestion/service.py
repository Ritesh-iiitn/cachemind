import hashlib
import shutil
import uuid
import logging
from pathlib import Path
from typing import List, Optional
import aiosqlite
from backend.app.core.config import settings
from backend.app.models.schemas import KnowledgeBaseResponse, DocumentResponse, DocumentChunk
from backend.app.ingestion.parser import DocumentParser
from backend.app.ingestion.chunker import TextChunker
from backend.app.ingestion.vector_store import VectorStore

logger = logging.getLogger("cachemind.ingestion")

class IngestionService:
    def __init__(self):
        self.chunker = TextChunker()

    @staticmethod
    def _compute_hash(file_path: Path) -> str:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for block in iter(lambda: f.read(65536), b""):
                hasher.update(block)
        return hasher.hexdigest()

    async def create_knowledge_base(self, name: str, description: Optional[str] = None) -> KnowledgeBaseResponse:
        kb_id = f"kb_{uuid.uuid4().hex[:10]}"
        async with aiosqlite.connect(settings.DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            await db.execute(
                "INSERT INTO knowledge_bases (id, name, description, version) VALUES (?, ?, ?, 1)",
                (kb_id, name, description)
            )
            await db.commit()
            async with db.execute("SELECT * FROM knowledge_bases WHERE id = ?", (kb_id,)) as cursor:
                row = await cursor.fetchone()
                return KnowledgeBaseResponse(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    version=row["version"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    document_count=0,
                    chunk_count=0
                )

    async def list_knowledge_bases(self) -> List[KnowledgeBaseResponse]:
        async with aiosqlite.connect(settings.DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            query = """
            SELECT kb.*, 
                   COUNT(DISTINCT d.id) as doc_count,
                   COUNT(DISTINCT c.id) as chk_count
            FROM knowledge_bases kb
            LEFT JOIN documents d ON kb.id = d.kb_id
            LEFT JOIN document_chunks c ON kb.id = c.kb_id
            GROUP BY kb.id
            ORDER BY kb.created_at DESC
            """
            async with db.execute(query) as cursor:
                rows = await cursor.fetchall()
                return [
                    KnowledgeBaseResponse(
                        id=r["id"],
                        name=r["name"],
                        description=r["description"],
                        version=r["version"],
                        created_at=r["created_at"],
                        updated_at=r["updated_at"],
                        document_count=r["doc_count"],
                        chunk_count=r["chk_count"]
                    )
                    for r in rows
                ]

    async def get_kb(self, kb_id: str) -> Optional[KnowledgeBaseResponse]:
        async with aiosqlite.connect(settings.DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM knowledge_bases WHERE id = ?", (kb_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                return KnowledgeBaseResponse(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    version=row["version"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"]
                )

    async def index_document(self, kb_id: str, file_path: Path, original_filename: str) -> DocumentResponse:
        doc_id = f"doc_{uuid.uuid4().hex[:10]}"
        content_hash = self._compute_hash(file_path)
        file_size = file_path.stat().st_size
        file_type = file_path.suffix.lstrip(".").lower() or "txt"
        
        # 1. Fetch current KB version
        kb = await self.get_kb(kb_id)
        if not kb:
            raise ValueError(f"Knowledge Base {kb_id} does not exist.")
            
        doc_version = 1
        
        # 2. Parse pages
        pages = DocumentParser.parse(file_path)
        
        # 3. Chunk
        chunks = self.chunker.chunk_document(
            pages=pages,
            document_id=doc_id,
            kb_id=kb_id,
            document_version=doc_version
        )
        
        # 4. Insert Document and Chunks into DB
        async with aiosqlite.connect(settings.DB_PATH) as db:
            await db.execute(
                """
                INSERT INTO documents (
                    id, kb_id, filename, file_type, file_size, version,
                    status, chunk_count, content_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (doc_id, kb_id, original_filename, file_type, file_size, doc_version, "indexed", len(chunks), content_hash)
            )
            
            for c in chunks:
                await db.execute(
                    """
                    INSERT INTO document_chunks (
                        id, document_id, kb_id, document_version, chunk_index,
                        page_number, section, text, token_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (c.id, c.document_id, c.kb_id, c.document_version, c.chunk_index, c.page_number, c.section, c.text, c.token_count)
                )
                
            # Increment KB version for atomic cache invalidation
            new_kb_version = kb.version + 1
            await db.execute("UPDATE knowledge_bases SET version = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_kb_version, kb_id))
            await db.commit()
            
        # 5. Add to FAISS Vector Store
        vstore = VectorStore(kb_id=kb_id, kb_version=new_kb_version)
        vstore.add_chunks(chunks)
        
        return DocumentResponse(
            id=doc_id,
            kb_id=kb_id,
            filename=original_filename,
            file_type=file_type,
            file_size=file_size,
            version=doc_version,
            status="indexed",
            chunk_count=len(chunks),
            content_hash=content_hash,
            created_at="",
            updated_at=""
        )

    async def list_documents(self, kb_id: str) -> List[DocumentResponse]:
        async with aiosqlite.connect(settings.DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM documents WHERE kb_id = ? ORDER BY created_at DESC", (kb_id,)) as cursor:
                rows = await cursor.fetchall()
                return [
                    DocumentResponse(
                        id=r["id"],
                        kb_id=r["kb_id"],
                        filename=r["filename"],
                        file_type=r["file_type"],
                        file_size=r["file_size"],
                        version=r["version"],
                        status=r["status"],
                        chunk_count=r["chunk_count"],
                        content_hash=r["content_hash"],
                        created_at=r["created_at"],
                        updated_at=r["updated_at"]
                    )
                    for r in rows
                ]

    async def delete_document(self, kb_id: str, doc_id: str) -> bool:
        async with aiosqlite.connect(settings.DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("DELETE FROM documents WHERE id = ? AND kb_id = ?", (doc_id, kb_id))
            deleted = cursor.rowcount > 0
            if deleted:
                # Increment KB version to trigger cache invalidation
                await db.execute("UPDATE knowledge_bases SET version = version + 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (kb_id,))
                await db.commit()
            return deleted

ingestion_service = IngestionService()
