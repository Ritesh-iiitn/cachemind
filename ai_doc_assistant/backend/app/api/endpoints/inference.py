from fastapi import APIRouter, Query
from backend.app.inference.kv_experiments import kv_benchmark_engine

router = APIRouter()

@router.get("/kv-benchmark")
async def run_kv_benchmark(
    prompt_tokens: int = Query(512, ge=64, le=4096),
    generated_tokens: int = Query(128, ge=16, le=1024),
    hidden_dim: int = Query(2048, ge=512, le=8192),
    num_heads: int = Query(16, ge=4, le=64)
):
    """
    Simulates and benchmarks transformer attention:
    Compares Naive O(N^2) Attention vs Stateful O(1) KV-Cache Attention.
    """
    return kv_benchmark_engine.run_kv_comparison(
        prompt_tokens=prompt_tokens,
        generated_tokens=generated_tokens,
        hidden_dim=hidden_dim,
        num_heads=num_heads
    )
