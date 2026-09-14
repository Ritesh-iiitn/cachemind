import json
import logging
import asyncio
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import StreamingResponse

from backend.app.queue.task_events import event_broadcaster

logger = logging.getLogger("cachemind.api.websocket")

router = APIRouter()


@router.websocket("/ws/jobs")
async def websocket_jobs_endpoint(websocket: WebSocket, job_id: Optional[str] = Query(None)):
    """
    Real-time WebSocket endpoint streaming job progress, status transitions, and lifecycle events.
    Supports filtering by specific job_id or receiving all cluster events.
    """
    await websocket.accept()
    queue = event_broadcaster.subscribe()
    logger.info(f"WebSocket client connected to /ws/jobs (filter_job_id={job_id})")

    # Send initial connection acknowledgment
    try:
        await websocket.send_json({
            "event_type": "connected",
            "message": "Connected to CacheMind Task Stream",
            "filter_job_id": job_id
        })
    except Exception:
        event_broadcaster.unsubscribe(queue)
        return

    async def receive_pings():
        try:
            while True:
                msg = await websocket.receive_text()
                try:
                    data = json.loads(msg)
                    if data.get("action") == "ping":
                        await websocket.send_json({"event_type": "pong"})
                except Exception:
                    pass
        except WebSocketDisconnect:
            pass
        except Exception:
            pass

    ping_task = asyncio.create_task(receive_pings())

    try:
        while True:
            event = await queue.get()
            # If client subscribed to specific job_id, filter others
            target_job = event.get("job_id")
            if job_id and target_job != job_id:
                continue

            await websocket.send_json(event)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected from /ws/jobs.")
    except Exception as e:
        logger.debug(f"WebSocket send error: {e}")
    finally:
        ping_task.cancel()
        event_broadcaster.unsubscribe(queue)


@router.get("/events/jobs", summary="Server-Sent Events (SSE) stream for job progress")
async def sse_jobs_stream(job_id: Optional[str] = Query(None)):
    """
    Server-Sent Events (SSE) fallback endpoint for clients behind proxies or HTTP-only environments.
    """
    queue = event_broadcaster.subscribe()

    async def event_generator():
        # Yield initial heartbeat
        yield f"data: {json.dumps({'event_type': 'connected', 'filter_job_id': job_id})}\n\n"
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    target_job = event.get("job_id")
                    if job_id and target_job != job_id:
                        continue
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # Keep-alive ping
                    yield ": ping\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            event_broadcaster.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
