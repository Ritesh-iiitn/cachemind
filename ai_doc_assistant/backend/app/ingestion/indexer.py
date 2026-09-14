import logging
from typing import List
import aiosqlite

from backend.app.core.config import settings
from backend.app.models.schemas import DocumentChunk
from backend.app.ingestion.vector_store import VectorStore

logger = logging.getLogger("cachemind.ingestion.indexer")


class DocumentIndexer:
    """
    Idempotent document indexer that atomically updates chunk metadata in SQLite
    and vector embeddings in the FAISS vector index.
    """

    @classmethod
    async def index_chunks(
        cls,
        kb_id: str,
        kb_version: int,
        document_id: str,
        document_version: int,
        chunks: List[DocumentChunk]
    ) -> int:
        """
        Idempotently inserts or updates document chunks in the database and vector store.
        If chunks previously existed for (document_id, document_version), they are replaced.
        """
        if not chunks:
            logger.warning(f"No chunks to index for document {document_id}")
            return 0

        async with aiosqlite.connect(settings.DB_PATH) as db:
            # 1. Idempotency guarantee: Remove any preexisting chunks for this doc version
            await db.execute(
                "DELETE FROM document_chunks WHERE document_id = ? AND document_version = ?",
                (document_id, document_version)
            )

            # 2. Insert new deterministic chunks
            for c in chunks:
                await db.execute(
                    """
                    INSERT INTO document_chunks (
                        id, document_id, kb_id, document_version, chunk_index,
                        page_number, section, text, token_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        c.id, c.document_id, c.kb_id, c.document_version, c.chunk_index,
                        c.page_number, c.section, c.text, c.token_count
                    )
                )

            # 3. Update document status and chunk count
            await db.execute(
                """
                UPDATE documents
                SET status = 'indexed',
                    chunk_count = ?,
                    version = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (len(chunks), document_version, document_id)
            )
            await db.commit()

        # 4. Add chunks to FAISS vector index for this KB version
        vstore = VectorStore(kb_id=kb_id, kb_version=kb_version)
        vstore.add_chunks(chunks)

        logger.info(
            f"Successfully indexed {len(chunks)} chunks for doc {document_id} into KB {kb_id} (v{kb_version})"
        )
        return len(chunks)


document_indexer = DocumentIndexer()
