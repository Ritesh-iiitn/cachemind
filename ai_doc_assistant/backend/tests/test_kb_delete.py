import pytest
import shutil
from pathlib import Path
from httpx import AsyncClient, ASGITransport
import aiosqlite

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.core.database import init_db
from backend.app.cache.exact_cache import exact_cache
from backend.app.cache.retrieval_cache import retrieval_cache
from backend.app.models.schemas import DocumentChunk


@pytest.mark.anyio
async def test_delete_knowledge_base_cascades_and_cleans():
    await init_db()

    kb_id = "kb_delete_test"
    kb_name = "To Be Deleted KB"
    doc_id = "doc_del_001"

    # 1. Insert KB, document, chunk, and ingestion job
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        await db.execute(
            "INSERT OR REPLACE INTO knowledge_bases (id, name, description, version) VALUES (?, ?, ?, ?)",
            (kb_id, kb_name, "Temporary KB for testing deletion", 1)
        )
        await db.execute(
            """INSERT OR REPLACE INTO documents (id, kb_id, filename, file_type, file_size, version, status, chunk_count, content_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (doc_id, kb_id, "notes.txt", "txt", 128, 1, "indexed", 1, "testhash123")
        )
        await db.execute(
            """INSERT OR REPLACE INTO document_chunks (id, document_id, kb_id, document_version, chunk_index, page_number, section, text, token_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("chk_del_001", doc_id, kb_id, 1, 0, 1, "Intro", "This chunk will be deleted", 10)
        )
        await db.execute(
            """INSERT OR REPLACE INTO ingestion_jobs (id, job_id, knowledge_base_id, document_id, status, current_stage)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("job_del_001", "job_del_001", kb_id, doc_id, "COMPLETED", "completed")
        )
        await db.commit()

    # 2. Populate mock files on disk and cache entries
    kb_doc_dir = settings.DOCUMENT_STORAGE / kb_id
    kb_doc_dir.mkdir(parents=True, exist_ok=True)
    test_file = kb_doc_dir / "notes.txt"
    test_file.write_text("Hello world to be deleted")

    vector_dir = settings.VECTOR_STORAGE / f"{kb_id}_v1"
    vector_dir.mkdir(parents=True, exist_ok=True)
    dummy_index = vector_dir / "index.faiss"
    dummy_index.write_bytes(b"dummy faiss index content")

    # Add cache entries
    exact_cache.put(kb_id, 1, "what is deleted?", {"kb_id": kb_id, "answer": "it is deleted"})
    dummy_chunk = DocumentChunk(
        id="chk_del_001", document_id=doc_id, kb_id=kb_id, document_version=1,
        chunk_index=0, page_number=1, section="Intro", text="This chunk will be deleted", token_count=10
    )
    retrieval_cache.put(kb_id, 1, "hybrid", 5, "what is deleted?", [dummy_chunk])

    assert exact_cache.get(kb_id, 1, "what is deleted?") is not None
    assert retrieval_cache.get(kb_id, 1, "hybrid", 5, "what is deleted?") is not None
    assert test_file.exists()
    assert dummy_index.exists()

    # 3. Call DELETE /api/v1/kb/{kb_id}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Initial check
        get_res = await client.get(f"/api/v1/kb/{kb_id}")
        assert get_res.status_code == 200
        assert get_res.json()["name"] == kb_name

        # Delete KB
        del_res = await client.delete(f"/api/v1/kb/{kb_id}")
        assert del_res.status_code == 200
        del_json = del_res.json()
        assert del_json["status"] == "success"
        assert kb_name in del_json["message"]

        # Subsequent GET should return 404
        get_after = await client.get(f"/api/v1/kb/{kb_id}")
        assert get_after.status_code == 404

        # Subsequent DELETE should return 404
        del_again = await client.delete(f"/api/v1/kb/{kb_id}")
        assert del_again.status_code == 404

    # 4. Verify SQLite cascading cleanup
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM knowledge_bases WHERE id = ?", (kb_id,)) as c:
            assert await c.fetchone() is None
        async with db.execute("SELECT * FROM documents WHERE kb_id = ?", (kb_id,)) as c:
            assert await c.fetchone() is None
        async with db.execute("SELECT * FROM document_chunks WHERE kb_id = ?", (kb_id,)) as c:
            assert await c.fetchone() is None
        async with db.execute("SELECT * FROM ingestion_jobs WHERE knowledge_base_id = ?", (kb_id,)) as c:
            assert await c.fetchone() is None

    # 5. Verify Disk file and Vector index cleanup
    assert not kb_doc_dir.exists()
    assert not vector_dir.exists()

    # 6. Verify Scoped Cache invalidation
    assert exact_cache.get(kb_id, 1, "what is deleted?") is None
    assert retrieval_cache.get(kb_id, 1, "hybrid", 5, "what is deleted?") is None
