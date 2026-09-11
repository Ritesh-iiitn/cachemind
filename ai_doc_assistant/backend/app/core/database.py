import aiosqlite
import logging
from pathlib import Path
from typing import AsyncGenerator
from backend.app.core.config import settings

logger = logging.getLogger("cachemind.database")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS knowledge_bases (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    kb_id TEXT NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL, -- 'pending', 'indexing', 'indexed', 'failed'
    chunk_count INTEGER DEFAULT 0,
    content_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS document_chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    kb_id TEXT NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    document_version INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    page_number INTEGER,
    section TEXT,
    text TEXT NOT NULL,
    token_count INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS execution_traces (
    request_id TEXT PRIMARY KEY,
    kb_id TEXT NOT NULL,
    query TEXT NOT NULL,
    plan_id TEXT NOT NULL,
    exact_cache_hit BOOLEAN DEFAULT 0,
    semantic_cache_hit BOOLEAN DEFAULT 0,
    retrieval_cache_hit BOOLEAN DEFAULT 0,
    prefix_cache_hit BOOLEAN DEFAULT 0,
    retrieval_strategy TEXT NOT NULL,
    model_used TEXT NOT NULL,
    verification_status TEXT NOT NULL,
    latency_ms REAL NOT NULL,
    tokens_generated INTEGER NOT NULL,
    tokens_saved INTEGER NOT NULL,
    estimated_cost_saved REAL NOT NULL,
    trace_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS benchmark_runs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    workload_type TEXT NOT NULL,
    total_queries INTEGER NOT NULL,
    baseline_p50_ms REAL,
    baseline_p95_ms REAL,
    optimized_p50_ms REAL,
    optimized_p95_ms REAL,
    cache_hit_rate REAL,
    compute_saved_pct REAL,
    report_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chunks_kb ON document_chunks(kb_id);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_kb ON documents(kb_id);
CREATE INDEX IF NOT EXISTS idx_traces_created ON execution_traces(created_at DESC);
"""

async def init_db() -> None:
    """Initialize the SQLite database with full schema and foreign key support."""
    logger.info(f"Initializing database at: {settings.DB_PATH}")
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        await db.executescript(SCHEMA_SQL)
        await db.commit()
    logger.info("Database initialized successfully.")

async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Dependency injection helper to yield an async database connection."""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON;")
        yield db
