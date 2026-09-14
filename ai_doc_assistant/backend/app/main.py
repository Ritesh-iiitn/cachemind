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
from backend.app.queue.queue_manager import queue_manager
from backend.app.workers.ingestion_tasks import ingestion_task_executor

async def embedded_worker_loop():
    """
    In-process background worker loop running within the FastAPI gateway.
    Consumes pending tasks from Redis or SQLite fallback, ensuring tasks complete
    even when running in single-process or local development without Docker.
    """
    logger.info("Embedded in-process background worker active.")
    while True:
        try:
            task_data = await queue_manager.dequeue(timeout_seconds=1.0)
            if task_data:
                job_id = task_data.get("job_id")
                if job_id:
                    logger.info(f"[gateway_worker] Dequeued task {job_id}")
                    await ingestion_task_executor.execute_job(
                        job_id=job_id,
                        worker_id="gateway_embedded_worker"
                    )
            else:
                await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Embedded worker loop error: {e}")
            await asyncio.sleep(2.0)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up CacheMind API Gateway...")
    await init_db()
    event_task = asyncio.create_task(event_broadcaster.start_redis_listener())
    worker_task = asyncio.create_task(embedded_worker_loop())
    logger.info("CacheMind ready to serve inference requests.")
    yield
    logger.info("Shutting down CacheMind API Gateway...")
    worker_task.cancel()
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

