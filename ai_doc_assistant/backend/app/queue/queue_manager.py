import time
import json
import logging
import asyncio
from typing import Optional, List, Dict, Any, Tuple

from backend.app.queue.redis_client import redis_manager

logger = logging.getLogger("cachemind.queue.manager")

# Queue Key Names
QUEUE_HIGH = "cachemind:queue:high"
QUEUE_DEFAULT = "cachemind:queue:default"
QUEUE_LOW = "cachemind:queue:low"
QUEUE_DELAYED = "cachemind:queue:delayed"
QUEUE_PROCESSING = "cachemind:queue:processing"
WORKER_HEARTBEATS = "cachemind:workers:heartbeats"


class QueueManager:
    """
    Production-grade Redis Queue Manager supporting:
    - Multi-priority FIFO queues (High, Default, Low)
    - Delayed/Scheduled queue with sorted set for exponential backoff retries
    - Active processing registry for crash detection
    - Worker heartbeat telemetry
    - Queue depth and backlog monitoring
    """

    @staticmethod
    def _queue_key_for_priority(priority: int) -> str:
        if priority >= 8:
            return QUEUE_HIGH
        elif priority <= 3:
            return QUEUE_LOW
        return QUEUE_DEFAULT

    async def enqueue(
        self,
        job_id: str,
        priority: int = 5,
        delay_seconds: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Enqueues a job. If delay_seconds > 0, places it into the delayed sorted set.
        Otherwise pushes directly to the priority list.
        """
        client = await redis_manager.get_client()
        payload = json.dumps({
            "job_id": job_id,
            "priority": priority,
            "enqueued_at": time.time(),
            "metadata": metadata or {}
        })

        if delay_seconds > 0:
            target_time = time.time() + delay_seconds
            await client.zadd(QUEUE_DELAYED, {payload: target_time})
            logger.info(f"Enqueued job {job_id} to DELAYED queue (exec in {delay_seconds:.1f}s)")
        else:
            q_key = self._queue_key_for_priority(priority)
            await client.rpush(q_key, payload)
            logger.info(f"Enqueued job {job_id} to {q_key} (priority {priority})")
        return True

    async def dequeue(self, timeout_seconds: float = 1.0) -> Optional[Dict[str, Any]]:
        """
        Consumes the next eligible job from priority queues (High -> Default -> Low).
        Also moves any mature delayed jobs into their respective priority queues.
        """
        client = await redis_manager.get_client()

        # 1. Promote mature delayed items
        await self._promote_delayed_tasks(client)

        # 2. Check High, Default, Low queues in priority order
        queues = [QUEUE_HIGH, QUEUE_DEFAULT, QUEUE_LOW]

        # Use non-blocking pop first
        for q in queues:
            raw = await client.lpop(q)
            if raw:
                try:
                    task_data = json.loads(raw)
                    # Register into processing set with timestamp
                    await client.hset(QUEUE_PROCESSING, task_data["job_id"], time.time())
                    return task_data
                except Exception as e:
                    logger.error(f"Malformed task payload in queue {q}: {e}")

        # If empty and timeout requested, short sleep
        if timeout_seconds > 0:
            await asyncio.sleep(min(timeout_seconds, 0.5))

        return None

    async def _promote_delayed_tasks(self, client) -> int:
        now = time.time()
        # Retrieve tasks whose target_time <= now
        items = await client.zrangebyscore(QUEUE_DELAYED, 0, now, start=0, num=50)
        promoted = 0
        for item in items:
            removed = await client.zrem(QUEUE_DELAYED, item)
            if removed:
                try:
                    task_data = json.loads(item)
                    priority = task_data.get("priority", 5)
                    q_key = self._queue_key_for_priority(priority)
                    await client.rpush(q_key, item)
                    promoted += 1
                except Exception as e:
                    logger.error(f"Failed to promote delayed task: {e}")
        return promoted

    async def ack(self, job_id: str) -> None:
        """Removes job from processing set upon completion or failure."""
        client = await redis_manager.get_client()
        await client.hdel(QUEUE_PROCESSING, job_id)

    async def get_queue_depth(self) -> int:
        """Returns total count of pending and delayed items across all queues."""
        try:
            client = await redis_manager.get_client()
            q_high = await client.llen(QUEUE_HIGH)
            q_default = await client.llen(QUEUE_DEFAULT)
            q_low = await client.llen(QUEUE_LOW)
            q_delayed = await client.zcard(QUEUE_DELAYED)
            return q_high + q_default + q_low + q_delayed
        except Exception:
            return 0

    async def register_worker_heartbeat(self, worker_id: str) -> None:
        try:
            client = await redis_manager.get_client()
            await client.hset(WORKER_HEARTBEATS, worker_id, time.time())
        except Exception as e:
            logger.debug(f"Heartbeat write failed: {e}")

    async def get_active_worker_count(self, freshness_seconds: float = 15.0) -> int:
        try:
            client = await redis_manager.get_client()
            heartbeats = await client.hgetall(WORKER_HEARTBEATS)
            now = time.time()
            active = 0
            for wid, last_seen in heartbeats.items():
                try:
                    if now - float(last_seen) <= freshness_seconds:
                        active += 1
                    else:
                        # Clean up stale worker heartbeat
                        await client.hdel(WORKER_HEARTBEATS, wid)
                except Exception:
                    pass
            return active
        except Exception:
            return 0

    async def clear_all(self) -> None:
        """Flushes all queues for test isolation."""
        client = await redis_manager.get_client()
        await client.delete(QUEUE_HIGH, QUEUE_DEFAULT, QUEUE_LOW, QUEUE_DELAYED, QUEUE_PROCESSING, WORKER_HEARTBEATS)


queue_manager = QueueManager()
