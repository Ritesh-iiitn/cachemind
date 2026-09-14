import json
import logging
import asyncio
from typing import Dict, Any, Callable, Set, Optional
from datetime import datetime, timezone

from backend.app.queue.redis_client import redis_manager

logger = logging.getLogger("cachemind.queue.events")

JOB_EVENTS_CHANNEL = "cachemind:job_events"


class TaskEventBroadcaster:
    """
    Publish/Subscribe event hub for distributed job lifecycle events.
    Enables instant WebSocket and SSE broadcasts across worker nodes and API gateways.
    """
    def __init__(self):
        self._subscribers: Set[asyncio.Queue] = set()
        self._redis_listener_task: Optional[asyncio.Task] = None
        self._is_listening = False

    async def emit_event(
        self,
        event_type: str,
        job_id: str,
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        payload = {
            "event_type": event_type,
            "job_id": job_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data or {}
        }
        msg_str = json.dumps(payload)

        # 1. Dispatch locally to in-process subscribers
        await self._dispatch_local(payload)

        # 2. Publish to Redis Pub/Sub channel for cross-process distribution
        try:
            client = await redis_manager.get_client()
            await client.publish(JOB_EVENTS_CHANNEL, msg_str)
        except Exception as e:
            logger.debug(f"Event broadcast to Redis failed: {e}")

    async def _dispatch_local(self, payload: Dict[str, Any]) -> None:
        dead_queues = set()
        for q in list(self._subscribers):
            try:
                if q.full():
                    try:
                        q.get_nowait()
                    except Exception:
                        pass
                q.put_nowait(payload)
            except Exception:
                dead_queues.add(q)
        for dq in dead_queues:
            self._subscribers.discard(dq)

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)

    async def start_redis_listener(self) -> None:
        if self._is_listening:
            return
        self._is_listening = True
        try:
            client = await redis_manager.get_client()
            pubsub = client.pubsub()
            await pubsub.subscribe(JOB_EVENTS_CHANNEL)

            async for message in pubsub.listen():
                if not self._is_listening:
                    break
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        await self._dispatch_local(data)
                    except Exception:
                        pass
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"Redis event listener error: {e}")
        finally:
            self._is_listening = False


event_broadcaster = TaskEventBroadcaster()
