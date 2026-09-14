import pytest
from backend.app.core.database import init_db
from backend.app.ingestion.chunker import TextChunker
from backend.app.ingestion.cleaner import TextCleaner
from backend.app.ingestion.parser import ParsedPage
from backend.app.ingestion.indexer import DocumentIndexer
from backend.app.models.schemas import DocumentChunk
import aiosqlite
from backend.app.core.config import settings


def test_deterministic_chunk_id_generation():
    doc_id = "doc_test_123"
    version = 1
    idx = 0

    id1 = TextChunker.generate_chunk_id(doc_id, version, idx)
    id2 = TextChunker.generate_chunk_id(doc_id, version, idx)
    assert id1 == id2
    assert id1.startswith("chk_")

    # Different index produces different ID
    id_other = TextChunker.generate_chunk_id(doc_id, version, 1)
    assert id1 != id_other

    # Different version produces different ID
    id_v2 = TextChunker.generate_chunk_id(doc_id, 2, idx)
    assert id1 != id_v2


def test_rechunking_produces_identical_chunks():
    chunker = TextChunker(target_chunk_size=100, chunk_overlap=20)
    pages = [
        ParsedPage(page_number=1, text="Distributed systems must tolerate network partitions and node failures. " * 10, section="Fault Tolerance"),
        ParsedPage(page_number=2, text="Consistency models range from strict linearizability to eventual consistency. " * 8, section="Consistency")
    ]

    run1 = chunker.chunk_document(pages, "doc_456", "kb_main", document_version=1)
    run2 = chunker.chunk_document(pages, "doc_456", "kb_main", document_version=1)

    assert len(run1) == len(run2)
    for c1, c2 in zip(run1, run2):
        assert c1.id == c2.id
        assert c1.chunk_index == c2.chunk_index
        assert c1.text == c2.text
        assert c1.page_number == c2.page_number


def test_text_cleaner_deterministic_sanitization():
    dirty_text = "Hello\x00\x08 world!\n\n\n\nThis is a   bullet • test – dash.\n\t"
    clean1 = TextCleaner.clean_text(dirty_text)
    clean2 = TextCleaner.clean_text(dirty_text)

    assert clean1 == clean2
    assert "\x00" not in clean1
    assert "\n\n\n" not in clean1
    assert "- test" in clean1


@pytest.mark.anyio
async def test_idempotent_indexer_prevents_duplicate_chunks():
    await init_db()
    kb_id = "kb_idemp_test"
    doc_id = "doc_idemp_test"
    doc_ver = 1
    kb_ver = 1

    # Prepare document record
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO knowledge_bases (id, name, version) VALUES (?, ?, ?)", (kb_id, "Test KB", kb_ver))
        await db.execute(
            """
            INSERT OR REPLACE INTO documents (id, kb_id, filename, file_type, file_size, version, status, chunk_count, content_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (doc_id, kb_id, "test.txt", "txt", 500, doc_ver, "pending", 0, "hash123")
        )
        await db.commit()

    chunk1 = DocumentChunk(
        id=TextChunker.generate_chunk_id(doc_id, doc_ver, 0),
        document_id=doc_id,
        kb_id=kb_id,
        document_version=doc_ver,
        chunk_index=0,
        page_number=1,
        section="Intro",
        text="Sample chunk content for idempotency testing.",
        token_count=10
    )

    # First indexing run
    indexed_count1 = await DocumentIndexer.index_chunks(
        kb_id=kb_id,
        kb_version=kb_ver,
        document_id=doc_id,
        document_version=doc_ver,
        chunks=[chunk1]
    )
    assert indexed_count1 == 1

    # Check chunk count in DB
    async with aiosqlite.connect(settings.DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM document_chunks WHERE document_id = ?", (doc_id,)) as cursor:
            row = await cursor.fetchone()
            assert row[0] == 1

    # Re-run same indexing (simulating duplicate task delivery)
    indexed_count2 = await DocumentIndexer.index_chunks(
        kb_id=kb_id,
        kb_version=kb_ver,
        document_id=doc_id,
        document_version=doc_ver,
        chunks=[chunk1]
    )
    assert indexed_count2 == 1

    # Check chunk count is still exactly 1, not 2
    async with aiosqlite.connect(settings.DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM document_chunks WHERE document_id = ?", (doc_id,)) as cursor:
            row = await cursor.fetchone()
            assert row[0] == 1
