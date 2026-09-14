import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.core.database import init_db
from backend.app.api.api import api_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("cachemind.main")

import asyncio
from backend.app.queue.task_events import event_broadcaster

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up CacheMind API Gateway...")
    await init_db()
    event_task = asyncio.create_task(event_broadcaster.start_redis_listener())
    logger.info("CacheMind ready to serve inference requests.")
    yield
    logger.info("Shutting down CacheMind API Gateway...")
    event_task.cancel()

app = FastAPI(
    title="CacheMind API Gateway",
    description="Adaptive Agentic RAG execution engine with intelligent multi-layer caching, model routing, and prefix/KV inference optimization.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local React Frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(api_router, prefix="/api")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "CacheMind",
        "version": settings.VERSION
    }

