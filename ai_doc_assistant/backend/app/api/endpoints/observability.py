import json
from typing import List, Dict, Any
import aiosqlite
from fastapi import APIRouter
from backend.app.models.schemas import ExecutionTrace
from backend.app.core.config import settings

router = APIRouter()

@router.get("/traces", response_model=List[ExecutionTrace])
async def list_traces(limit: int = 50):
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM execution_traces ORDER BY created_at DESC LIMIT ?", (limit,)) as cursor:
            rows = await cursor.fetchall()
            traces = []
            for r in rows:
                try:
                    trace_meta = json.loads(r["trace_json"])
                    traces.append(
                        ExecutionTrace(
                            request_id=r["request_id"],
                            kb_id=r["kb_id"],
                            query=r["query"],
                            plan_id=r["plan_id"],
                            exact_cache_hit=bool(r["exact_cache_hit"]),
                            semantic_cache_hit=bool(r["semantic_cache_hit"]),
                            retrieval_cache_hit=bool(r["retrieval_cache_hit"]),
                            prefix_cache_hit=bool(r["prefix_cache_hit"]),
                            retrieval_strategy=r["retrieval_strategy"],
                            model_used=r["model_used"],
                            verification_status=r["verification_status"],
                            latency_ms=r["latency_ms"],
                            tokens_generated=r["tokens_generated"],
                            tokens_saved=r["tokens_saved"],
                            estimated_cost_saved=r["estimated_cost_saved"],
                            steps=trace_meta.get("steps", []),
                            created_at=r["created_at"]
                        )
                    )
                except Exception:
                    pass
            return traces

@router.get("/metrics")
async def get_metrics_summary():
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT 
                COUNT(*) as total_requests,
                AVG(latency_ms) as avg_latency_ms,
                SUM(exact_cache_hit) as exact_hits,
                SUM(semantic_cache_hit) as semantic_hits,
                SUM(retrieval_cache_hit) as retrieval_hits,
                SUM(tokens_saved) as tokens_saved,
                SUM(estimated_cost_saved) as cost_saved
            FROM execution_traces
        """) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else {}
