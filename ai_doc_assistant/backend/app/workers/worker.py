import sys
import os
import signal
import uuid
import asyncio
import logging
from typing import Optional

from backend.app.core.config import settings
from backend.app.core.database import init_db
from backend.app.queue.queue_manager import queue_manager
from backend.app.workers.ingestion_tasks import ingestion_task_executor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s"
)
logger = logging.getLogger("cachemind.worker")


class IngestionWorker:
    """
    Production-grade background worker for consuming and processing asynchronous document ingestion jobs.
    Features:
    - Graceful shutdown signal handling (SIGINT, SIGTERM)
    - Background heartbeat pulse for cluster discovery
    - Multi-priority queue consumption (High -> Default -> Low -> Delayed)
    - In-flight execution tracking and crash recovery
    - Concurrency throttle
    """

    def __init__(self, worker_id: Optional[str] = None, concurrency: int = 2):
        self.worker_id = worker_id or f"worker_{uuid.uuid4().hex[:8]}"
        self.concurrency = concurrency
        self.is_running = False
        self._semaphore = asyncio.Semaphore(concurrency)
        self._active_tasks = set()
        self._heartbeat_task: Optional[asyncio.Task] = None

    async def _heartbeat_loop(self) -> None:
        """Pulse heartbeat every 5 seconds to keep worker registered as active."""
        while self.is_running:
            try:
                await queue_manager.register_worker_heartbeat(self.worker_id)
            except Exception as e:
                logger.debug(f"Heartbeat pulse failed: {e}")
            await asyncio.sleep(5.0)

    async def _process_task_wrapper(self, task_data: dict) -> None:
        job_id = task_data.get("job_id")
        if not job_id:
            return

        async with self._semaphore:
            logger.info(f"[{self.worker_id}] Dequeued and acquired lock for job: {job_id}")
            try:
                await ingestion_task_executor.execute_job(job_id=job_id, worker_id=self.worker_id)
            except Exception as e:
                logger.error(f"[{self.worker_id}] Unhandled error executing job {job_id}: {e}")
            finally:
                logger.info(f"[{self.worker_id}] Finished processing job: {job_id}")

    async def start(self) -> None:
        """Main worker event loop."""
        self.is_running = True
        logger.info(f"Starting Ingestion Worker [{self.worker_id}] (concurrency={self.concurrency})...")

        # Ensure database tables exist
        await init_db()

        # Start heartbeat
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        logger.info(f"Worker [{self.worker_id}] ready and polling Redis queue...")

        while self.is_running:
            try:
                # Consume next available task
                task_data = await queue_manager.dequeue(timeout_seconds=1.0)
                if task_data:
                    task = asyncio.create_task(self._process_task_wrapper(task_data))
                    self._active_tasks.add(task)
                    task.add_done_callback(self._active_tasks.discard)
                else:
                    await asyncio.sleep(0.2)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker poll loop error: {e}")
                await asyncio.sleep(1.0)

        logger.info(f"Worker [{self.worker_id}] exited main polling loop.")
        await self._shutdown()

    async def _shutdown(self) -> None:
        """Gracefully wait for in-flight tasks to complete."""
        logger.info(f"Worker [{self.worker_id}] shutting down. Waiting for {len(self._active_tasks)} active tasks...")
        if self._heartbeat_task:
            self._heartbeat_task.cancel()

        if self._active_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._active_tasks, return_exceptions=True),
                    timeout=15.0
                )
            except asyncio.TimeoutError:
                logger.warning("Timed out waiting for in-flight tasks during shutdown.")

        logger.info(f"Worker [{self.worker_id}] shutdown complete.")

    def stop(self) -> None:
        self.is_running = False


# Arq worker integration definition
async def arq_ingest_document(ctx, job_id: str):
    """Arq task function entrypoint."""
    worker_id = ctx.get("worker_id", "arq_worker")
    await ingestion_task_executor.execute_job(job_id=job_id, worker_id=worker_id)


class WorkerSettings:
    functions = [arq_ingest_document]
    redis_settings = None  # Will be configured from settings.REDIS_URL
    max_jobs = 4


def main():
    """CLI entry point for running the worker directly."""
    worker = IngestionWorker()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def handle_signal(sig, frame):
        logger.info(f"Received shutdown signal ({signal.Signals(sig).name}). Triggering graceful stop...")
        worker.stop()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        loop.run_until_complete(worker.start())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()


if __name__ == "__main__":
    main()
