from fastapi import APIRouter
from backend.app.api.endpoints import kb, query, cache, benchmark, observability, inference

api_router = APIRouter()

api_router.include_router(kb.router, prefix="/kb", tags=["Knowledge Base"])
api_router.include_router(query.router, prefix="/query", tags=["Query & Agentic RAG"])
api_router.include_router(cache.router, prefix="/cache", tags=["Multi-Layer Caching"])
api_router.include_router(benchmark.router, prefix="/benchmark", tags=["Benchmarking"])
api_router.include_router(observability.router, prefix="/observability", tags=["Observability & Tracing"])
api_router.include_router(inference.router, prefix="/inference", tags=["Inference & KV Cache"])
