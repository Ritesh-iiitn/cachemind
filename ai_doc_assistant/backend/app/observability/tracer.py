import time
import json
import logging
import uuid
from typing import Dict, Any, List, Optional
import aiosqlite
from backend.app.core.config import settings
from backend.app.models.schemas import TraceStep, ExecutionTrace

logger = logging.getLogger("cachemind.tracer")

class RequestTracer:
    """
    High-resolution request tracer that records micro-timings, cache statuses,
    routing decisions, LLM stats, and persists structured execution traces.
    """
    def __init__(self, request_id: Optional[str] = None, kb_id: str = "", query: str = ""):
        self.request_id = request_id or f"req_{uuid.uuid4().hex[:12]}"
        self.kb_id = kb_id
        self.query = query
        self.start_time = time.perf_counter()
        self.end_time: Optional[float] = None
        self.steps: List[TraceStep] = []
        self._current_step_name: Optional[str] = None
        self._current_step_start: Optional[float] = None
        
        # Status flags
        self.plan_id: str = "default_plan"
        self.exact_cache_hit: bool = False
        self.semantic_cache_hit: bool = False
        self.retrieval_cache_hit: bool = False
        self.prefix_cache_hit: bool = False
        self.retrieval_strategy: str = "none"
        self.model_used: str = "none"
        self.verification_status: str = "SKIPPED"
        self.tokens_generated: int = 0
        self.tokens_saved: int = 0
        self.estimated_cost_saved: float = 0.0

    def start_step(self, step_name: str) -> None:
        if self._current_step_name is not None:
            self.end_step()
        self._current_step_name = step_name
        self._current_step_start = time.perf_counter()

    def end_step(self, details: Optional[Dict[str, Any]] = None) -> None:
        if self._current_step_name is not None and self._current_step_start is not None:
            duration_ms = (time.perf_counter() - self._current_step_start) * 1000.0
            self.steps.append(
                TraceStep(
                    step_name=self._current_step_name,
                    started_at=self._current_step_start - self.start_time,
                    duration_ms=round(duration_ms, 2),
                    details=details or {}
                )
            )
            self._current_step_name = None
            self._current_step_start = None

    def get_total_latency_ms(self) -> float:
        if self.end_time is not None:
            return round((self.end_time - self.start_time) * 1000.0, 2)
        return round((time.perf_counter() - self.start_time) * 1000.0, 2)

    def get_latency_breakdown(self) -> Dict[str, float]:
        breakdown = {}
        for step in self.steps:
            breakdown[step.step_name] = step.duration_ms
        return breakdown

    def finish(self) -> "RequestTracer":
        if self._current_step_name is not None:
            self.end_step()
        self.end_time = time.perf_counter()
        
        # Compute token / cost savings estimation
        if self.exact_cache_hit or self.semantic_cache_hit:
            self.tokens_saved = self.tokens_generated if self.tokens_generated > 0 else 350
            # Approx $0.002 per 1k tokens saved
            self.estimated_cost_saved = (self.tokens_saved / 1000.0) * 0.002
        elif self.retrieval_cache_hit:
            self.tokens_saved = 150
            self.estimated_cost_saved = 0.0003
        return self

    async def persist_to_db(self) -> None:
        """Persist execution trace record into SQLite."""
        self.finish()
        total_lat = self.get_total_latency_ms()
        trace_dict = {
            "request_id": self.request_id,
            "kb_id": self.kb_id,
            "query": self.query,
            "plan_id": self.plan_id,
            "latency_ms": total_lat,
            "steps": [s.model_dump() for s in self.steps],
            "latency_breakdown": self.get_latency_breakdown()
        }
        
        try:
            async with aiosqlite.connect(settings.DB_PATH) as db:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO execution_traces (
                        request_id, kb_id, query, plan_id, exact_cache_hit,
                        semantic_cache_hit, retrieval_cache_hit, prefix_cache_hit,
                        retrieval_strategy, model_used, verification_status,
                        latency_ms, tokens_generated, tokens_saved, estimated_cost_saved,
                        trace_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        self.request_id,
                        self.kb_id,
                        self.query,
                        self.plan_id,
                        1 if self.exact_cache_hit else 0,
                        1 if self.semantic_cache_hit else 0,
                        1 if self.retrieval_cache_hit else 0,
                        1 if self.prefix_cache_hit else 0,
                        self.retrieval_strategy,
                        self.model_used,
                        self.verification_status,
                        total_lat,
                        self.tokens_generated,
                        self.tokens_saved,
                        self.estimated_cost_saved,
                        json.dumps(trace_dict)
                    )
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to persist trace {self.request_id}: {e}")
