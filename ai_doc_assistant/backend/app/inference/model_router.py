import re
import logging
from typing import Dict, Any, Literal, Tuple
from backend.app.core.config import settings

logger = logging.getLogger("cachemind.model_router")

class ModelRouter:
    """
    Intelligent Model Router selecting optimal local model tiers
    (Small, Medium, Large) based on query complexity, context token budget,
    and required reasoning depth.
    """
    def __init__(self):
        self.model_tiers = {
            "small": settings.DEFAULT_SMALL_MODEL,
            "medium": settings.DEFAULT_MEDIUM_MODEL,
            "large": settings.DEFAULT_LARGE_MODEL,
        }

    def route_query(
        self,
        query: str,
        context_token_count: int = 0,
        force_tier: Literal["small", "medium", "large"] = None
    ) -> Tuple[str, str, str]:
        """
        Returns (tier_name, model_identifier, routing_reason).
        """
        if force_tier in self.model_tiers:
            return force_tier, self.model_tiers[force_tier], f"forced_override_{force_tier}"

        q_lower = query.lower()

        # Complex reasoning / multi-hop comparison -> Large model
        if re.search(r"\b(compare|contrast|synthesize|evaluate|tradeoffs|architecture analysis|differences between)\b", q_lower) or context_token_count > 3000:
            tier = "large"
            reason = "complex_reasoning_and_synthesis"
        # Standard factual / summarization -> Medium model
        elif re.search(r"\b(how to|explain|summarize|why does|describe|details on)\b", q_lower) or context_token_count > 800:
            tier = "medium"
            reason = "standard_factual_explanation"
        # Simple short lookup / definition -> Small model
        else:
            tier = "small"
            reason = "simple_fact_lookup"

        model_name = self.model_tiers[tier]
        logger.info(f"[ModelRouter] Query: '{query[:30]}...' -> Routed to {tier.upper()} ({model_name}) Reason: {reason}")
        return tier, model_name, reason

model_router = ModelRouter()
