import re
import logging
from typing import Dict, Any, Optional
from backend.app.models.schemas import ExecutionPlan, QueryRequest
from backend.app.core.config import settings
from backend.app.cache.exact_cache import exact_cache
from backend.app.cache.semantic_cache import semantic_cache
from backend.app.inference.model_router import model_router

logger = logging.getLogger("cachemind.planner")

class CacheAwarePlanner:
    """
    Evaluates multi-layer cache candidates, query complexity, latency budget,
    and constructs an optimal Execution Plan prior to executing expensive operations.
    """
    def create_plan(
        self,
        request: QueryRequest,
        kb_version: int = 1
    ) -> ExecutionPlan:
        query = request.query.strip()
        q_lower = query.lower()
        
        # 1. Evaluate Complexity
        if re.search(r"\b(compare|contrast|synthesize|tradeoffs|differences between|across multiple)\b", q_lower):
            complexity = "multi_hop"
        elif len(query.split()) > 15 or "?" in query and len(query.split()) > 10:
            complexity = "complex"
        elif re.search(r"\b(how to|explain|summarize|details on)\b", q_lower):
            complexity = "moderate"
        else:
            complexity = "simple"

        # 2. Select Retrieval Strategy
        if request.force_strategy:
            strategy = request.force_strategy
            use_reranker = True
        elif complexity == "multi_hop":
            strategy = "hybrid"
            use_reranker = True
        elif complexity == "complex":
            strategy = "hybrid"
            use_reranker = True
        elif re.search(r"\b(error|code|id|version|number|tag|status)\b", q_lower):
            strategy = "bm25"
            use_reranker = False
        else:
            strategy = "dense"
            use_reranker = False

        # 3. Model Tier Routing
        tier, model_name, _ = model_router.route_query(
            query=query,
            force_tier=request.force_model
        )

        # 4. Verification Requirement
        verification_required = (complexity in ["complex", "multi_hop"])

        # 5. Cache Candidates
        candidates = []
        if not request.force_no_cache:
            candidates.append("L1_exact")
            candidates.append("L2_semantic")
            candidates.append("L4_retrieval")
            candidates.append("L5_prefix")

        plan_id = f"plan_{strategy}_{tier}_{complexity}"
        reason = f"Routed query of {complexity} complexity to {strategy.upper()} retrieval using {tier.upper()} model ({model_name})."

        estimated_latency = 1200.0 if complexity == "multi_hop" else (600.0 if complexity == "complex" else 250.0)

        plan = ExecutionPlan(
            plan_id=plan_id,
            reason=reason,
            query_complexity=complexity,
            retrieval_strategy=strategy,
            use_reranker=use_reranker,
            model_tier=tier,
            model_name=model_name,
            verification_required=verification_required,
            estimated_latency_ms=estimated_latency,
            cache_candidates=candidates
        )
        
        logger.info(f"[Planner] Generated Plan: {plan.plan_id} -> Strategy: {strategy}, Model: {model_name}")
        return plan

planner = CacheAwarePlanner()
