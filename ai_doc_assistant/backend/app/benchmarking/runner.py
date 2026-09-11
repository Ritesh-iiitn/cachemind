import time
import json
import uuid
import logging
import numpy as np
import aiosqlite
from typing import List, Dict, Any, Optional
from backend.app.core.config import settings
from backend.app.models.schemas import (
    BenchmarkRunRequest, BenchmarkReport, BenchmarkResultItem,
    QueryRequest
)
from backend.app.agents.graph import agentic_engine
from backend.app.retrieval.dense import dense_retriever
from backend.app.inference.llama_client import llama_client
from backend.app.ingestion.service import ingestion_service

logger = logging.getLogger("cachemind.benchmark")

DEFAULT_BENCHMARK_QUERIES = [
    "What is the high-level architecture of the system?",
    "What is the high-level architecture of the system?",  # Exact Repeat
    "Can you explain the system architecture in detail?",    # Semantic Paraphrase
    "What are the multi-layer caching tiers supported?",
    "Explain the difference between L1 exact cache and L2 semantic cache.",
    "Compare the scalability tradeoffs and retrieval performance.",
    "How does the query planner decide between dense and BM25 search?",
    "What are the multi-layer caching tiers supported?",    # Exact Repeat
    "Explain the difference between L1 exact cache and L2 semantic cache.", # Exact Repeat
    "What verification steps are performed before admitting a response to cache?"
]

class BenchmarkRunner:
    """
    Automated side-by-side benchmark runner comparing Baseline RAG
    versus CacheMind across latency, cache efficiency, and compute savings.
    """
    
    async def run_baseline_query(self, kb_id: str, kb_version: int, query: str) -> Dict[str, Any]:
        t0 = time.perf_counter()
        # Simple RAG: Always retrieve dense -> Always call default model (No cache)
        chunks = dense_retriever.retrieve(kb_id, kb_version, query, top_k=3)
        context = "\n\n".join([c.text for c in chunks])
        prompt = f"Context:\n{context}\n\nQuestion: {query}"
        res = await llama_client.generate(prompt=prompt, model="qwen2.5:3b")
        total_lat_ms = (time.perf_counter() - t0) * 1000.0
        return {
            "latency_ms": round(total_lat_ms, 2),
            "tokens_generated": res["tokens_generated"]
        }

    async def run_benchmark(self, request: BenchmarkRunRequest) -> BenchmarkReport:
        kb = await ingestion_service.get_kb(request.kb_id)
        if not kb:
            raise ValueError(f"Knowledge Base {request.kb_id} not found.")

        run_id = f"bench_{uuid.uuid4().hex[:10]}"
        queries = DEFAULT_BENCHMARK_QUERIES[:request.queries_count]

        baseline_latencies = []
        optimized_latencies = []
        detailed_items: List[BenchmarkResultItem] = []
        cache_hits = 0
        total_tokens_saved = 0

        logger.info(f"Starting Benchmark {run_id} with {len(queries)} queries...")

        for q in queries:
            # 1. Run Baseline (No Caching, Naive Dense)
            base_res = await self.run_baseline_query(request.kb_id, kb.version, q)
            baseline_latencies.append(base_res["latency_ms"])

            # 2. Run CacheMind Optimized Engine
            q_req = QueryRequest(kb_id=request.kb_id, query=q)
            opt_res = await agentic_engine.execute_query(q_req)
            optimized_latencies.append(opt_res.total_latency_ms)

            is_hit = (opt_res.cache_status.exact_cache_hit or 
                      opt_res.cache_status.semantic_cache_hit or 
                      opt_res.cache_status.retrieval_cache_hit)
            if is_hit:
                cache_hits += 1
            total_tokens_saved += opt_res.tokens_saved

            reduc = ((base_res["latency_ms"] - opt_res.total_latency_ms) / base_res["latency_ms"]) * 100.0 if base_res["latency_ms"] > 0 else 0.0

            tier_label = opt_res.cache_status.cache_tier_matched or "MISS"

            detailed_items.append(
                BenchmarkResultItem(
                    query=q,
                    baseline_latency_ms=base_res["latency_ms"],
                    optimized_latency_ms=opt_res.total_latency_ms,
                    cache_tier=tier_label,
                    model_used=opt_res.model_used,
                    latency_reduction_pct=round(max(0.0, reduc), 2),
                    tokens_saved=opt_res.tokens_saved
                )
            )

        # Statistical Calculations
        base_p50 = float(np.percentile(baseline_latencies, 50))
        base_p95 = float(np.percentile(baseline_latencies, 95))
        base_avg = float(np.mean(baseline_latencies))

        opt_p50 = float(np.percentile(optimized_latencies, 50))
        opt_p95 = float(np.percentile(optimized_latencies, 95))
        opt_avg = float(np.mean(optimized_latencies))

        hit_rate = round((cache_hits / len(queries)) * 100.0, 2)
        compute_saved_pct = round(((base_avg - opt_avg) / base_avg) * 100.0, 2) if base_avg > 0 else 0.0

        report = BenchmarkReport(
            id=run_id,
            name=request.name,
            workload_type=request.workload_type,
            total_queries=len(queries),
            baseline_p50_ms=round(base_p50, 2),
            baseline_p95_ms=round(base_p95, 2),
            baseline_avg_ms=round(base_avg, 2),
            optimized_p50_ms=round(opt_p50, 2),
            optimized_p95_ms=round(opt_p95, 2),
            optimized_avg_ms=round(opt_avg, 2),
            cache_hit_rate=hit_rate,
            compute_saved_pct=max(0.0, compute_saved_pct),
            detailed_results=detailed_items,
            created_at=time.strftime("%Y-%m-%d %H:%M:%S")
        )

        # Persist to SQLite
        try:
            async with aiosqlite.connect(settings.DB_PATH) as db:
                await db.execute(
                    """
                    INSERT INTO benchmark_runs (
                        id, name, workload_type, total_queries,
                        baseline_p50_ms, baseline_p95_ms, optimized_p50_ms, optimized_p95_ms,
                        cache_hit_rate, compute_saved_pct, report_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        report.id, report.name, report.workload_type, report.total_queries,
                        report.baseline_p50_ms, report.baseline_p95_ms, report.optimized_p50_ms, report.optimized_p95_ms,
                        report.cache_hit_rate, report.compute_saved_pct, report.model_dump_json()
                    )
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to persist benchmark run {run_id}: {e}")

        logger.info(f"Benchmark {run_id} completed. Cache Hit Rate: {hit_rate}%, Compute Saved: {compute_saved_pct}%")
        return report

benchmark_runner = BenchmarkRunner()
