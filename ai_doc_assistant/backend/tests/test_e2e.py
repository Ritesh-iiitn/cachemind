import pytest
from pathlib import Path
from backend.app.core.database import init_db
from backend.app.ingestion.service import ingestion_service
from backend.app.agents.graph import agentic_engine
from backend.app.benchmarking.runner import benchmark_runner
from backend.app.models.schemas import QueryRequest, BenchmarkRunRequest

@pytest.mark.anyio
async def test_end_to_end_flow():
    # 1. Initialize DB
    await init_db()
    
    # 2. Create Knowledge Base
    kb = await ingestion_service.create_knowledge_base("E2E Test KB", "Testing end to end flow")
    assert kb.id is not None
    assert kb.version == 1
    
    # 3. Index Sample Knowledge File
    sample_path = Path(__file__).resolve().parent.parent.parent / "benchmarks" / "datasets" / "sample_knowledge.md"
    doc = await ingestion_service.index_document(kb.id, sample_path, "sample_knowledge.md")
    assert doc.id is not None
    assert doc.chunk_count > 0
    
    # 4. First Query (Cold - MISS)
    req1 = QueryRequest(kb_id=kb.id, query="What is the high-level architecture of CacheMind?")
    res1 = await agentic_engine.execute_query(req1)
    assert res1.cache_status.exact_cache_hit is False
    assert res1.answer is not None
    assert len(res1.citations) > 0
    
    # 5. Exact Repeat Query (Exact HIT)
    res2 = await agentic_engine.execute_query(req1)
    assert res2.cache_status.exact_cache_hit is True
    assert res2.total_latency_ms < res1.total_latency_ms
    
    # 6. Semantic Paraphrase Query (Semantic HIT)
    req3 = QueryRequest(kb_id=kb.id, query="Can you explain the system architecture in CacheMind?")
    res3 = await agentic_engine.execute_query(req3)
    assert res3.cache_status.semantic_cache_hit is True
    
    # 7. Run Benchmark Workload
    bench_req = BenchmarkRunRequest(kb_id=kb.id, queries_count=4, workload_type="mixed")
    report = await benchmark_runner.run_benchmark(bench_req)
    assert report.total_queries == 4
    assert report.compute_saved_pct >= 0.0
