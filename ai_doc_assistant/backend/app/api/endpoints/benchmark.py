import json
from typing import List
import aiosqlite
from fastapi import APIRouter, HTTPException, status
from backend.app.models.schemas import BenchmarkRunRequest, BenchmarkReport
from backend.app.benchmarking.runner import benchmark_runner
from backend.app.core.config import settings

router = APIRouter()

@router.post("/run", response_model=BenchmarkReport)
async def run_benchmark(request: BenchmarkRunRequest):
    try:
        report = await benchmark_runner.run_benchmark(request)
        return report
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Benchmark execution failed: {str(e)}")

@router.get("/history", response_model=List[BenchmarkReport])
async def list_benchmark_history():
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT report_json FROM benchmark_runs ORDER BY created_at DESC LIMIT 20") as cursor:
            rows = await cursor.fetchall()
            reports = []
            for r in rows:
                try:
                    data = json.loads(r["report_json"])
                    reports.append(BenchmarkReport(**data))
                except Exception:
                    pass
            return reports
