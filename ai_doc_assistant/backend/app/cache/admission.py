import re
import time
import logging
from typing import Dict, Any, Tuple
from backend.app.core.config import settings

logger = logging.getLogger("cachemind.admission")

class CacheAdmissionPolicy:
    """
    Intelligent Cost-Aware Cache Admission Controller.
    Determines whether a generated answer deserves entry into L1/L2 caches
    based on query stability, execution cost, entity richness, and volatility.
    """
    def __init__(self):
        self.min_generation_cost_ms = settings.ADMISSION_MIN_GENERATION_COST_MS
        self.query_frequency_map: Dict[str, int] = {}

    def record_query(self, normalized_query: str) -> int:
        count = self.query_frequency_map.get(normalized_query, 0) + 1
        self.query_frequency_map[normalized_query] = count
        return count

    def should_admit(
        self,
        query: str,
        generation_latency_ms: float,
        tokens_generated: int,
        verification_status: str
    ) -> Tuple[bool, str, int]:
        """
        Evaluates admission criteria. Returns (should_admit, reason, recommended_ttl).
        """
        # 1. Do not cache failed or unverified hallucinations
        if verification_status == "FAILED":
            return False, "verification_failed", 0

        # 2. Check for real-time / temporal volatile triggers
        volatile_keywords = ["today", "now", "current time", "yesterday", "live status", "realtime", "latest minute"]
        q_lower = query.lower()
        if any(w in q_lower for w in volatile_keywords):
            return False, "volatile_temporal_query", 0

        # 3. Check for ultra-low latency or trivial outputs (not worth storing)
        if generation_latency_ms < 5.0 and tokens_generated < 5:
            return False, "generation_cost_too_low", 0

        # 4. Determine Recommended TTL based on query type
        if re.search(r"\b(define|definition|what is|how to|explain|overview|architecture)\b", q_lower):
            # Stable conceptual query -> High TTL (3 days)
            ttl = 86400 * 3
            reason = "stable_conceptual_query"
        elif re.search(r"\b(compare|contrast|tradeoffs|difference|benchmark)\b", q_lower):
            # Synthesis query -> Medium TTL (1 day)
            ttl = 86400
            reason = "synthesis_query"
        else:
            # Default TTL (12 hours)
            ttl = 43200
            reason = "standard_query"

        logger.info(f"[Admission ADMIT] Query: '{query[:30]}...' Reason: {reason}, TTL: {ttl}s")
        return True, reason, ttl

admission_controller = CacheAdmissionPolicy()
