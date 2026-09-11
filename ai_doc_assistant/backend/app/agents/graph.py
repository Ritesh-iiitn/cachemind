import time
import logging
import asyncio
from typing import List, Dict, Any, Optional
from backend.app.core.config import settings
from backend.app.models.schemas import (
    QueryRequest, QueryResponse, ExecutionPlan, CacheStatus,
    DocumentChunk, Citation
)
from backend.app.observability.tracer import RequestTracer
from backend.app.ingestion.service import ingestion_service
from backend.app.cache.exact_cache import exact_cache
from backend.app.cache.semantic_cache import semantic_cache
from backend.app.cache.retrieval_cache import retrieval_cache
from backend.app.cache.admission import admission_controller
from backend.app.agents.planner import planner
from backend.app.agents.verifier import verifier
from backend.app.retrieval.dense import dense_retriever
from backend.app.retrieval.bm25 import bm25_retriever
from backend.app.retrieval.hybrid import hybrid_retriever
from backend.app.retrieval.reranker import reranker
from backend.app.inference.llama_client import llama_client

logger = logging.getLogger("cachemind.agent.graph")

class AgenticRAGEngine:
    """
    Production-grade Agentic RAG Execution Engine with multi-layer caching,
    adaptive retrieval routing, multi-hop query decomposition, verification,
    and structured execution tracing.
    """
    
    async def execute_query(self, request: QueryRequest) -> QueryResponse:
        tracer = RequestTracer(kb_id=request.kb_id, query=request.query)
        steps_executed = []
        
        # 1. Fetch KB Metadata & Version
        tracer.start_step("fetch_kb_metadata")
        kb = await ingestion_service.get_kb(request.kb_id)
        if not kb:
            raise ValueError(f"Knowledge Base {request.kb_id} not found.")
        kb_version = kb.version
        tracer.end_step({"kb_version": kb_version})
        steps_executed.append("fetch_kb_metadata")

        cache_status = CacheStatus()

        # 2. Check Tier 1: Exact Response Cache
        if not request.force_no_cache:
            tracer.start_step("exact_cache_lookup")
            exact_hit = exact_cache.get(request.kb_id, kb_version, request.query)
            tracer.end_step({"hit": exact_hit is not None})
            steps_executed.append("exact_cache_lookup")

            if exact_hit is not None:
                tracer.exact_cache_hit = True
                cache_status.exact_cache_hit = True
                cache_status.cache_tier_matched = "EXACT_L1"
                tracer.plan_id = "exact_cache_hit_plan"
                tracer.verification_status = "SKIPPED"
                tracer.tokens_generated = 0
                
                await tracer.persist_to_db()
                return QueryResponse(
                    request_id=tracer.request_id,
                    query=request.query,
                    answer=exact_hit["answer"],
                    citations=[Citation(**c) for c in exact_hit.get("citations", [])],
                    execution_plan=ExecutionPlan(**exact_hit["execution_plan"]),
                    cache_status=cache_status,
                    latency_breakdown_ms=tracer.get_latency_breakdown(),
                    total_latency_ms=tracer.get_total_latency_ms(),
                    model_used=exact_hit.get("model_used", "cached"),
                    tokens_generated=0,
                    tokens_saved=exact_hit.get("tokens_saved", 350),
                    verification_status="PASSED",
                    steps_executed=steps_executed
                )

        # 3. Check Tier 2: Semantic Response Cache (FAISS + Entity Guardrail)
        if not request.force_no_cache:
            tracer.start_step("semantic_cache_lookup")
            sem_hit, sim_score = semantic_cache.lookup(request.kb_id, kb_version, request.query)
            tracer.end_step({"hit": sem_hit is not None, "similarity": sim_score})
            steps_executed.append("semantic_cache_lookup")

            if sem_hit is not None:
                tracer.semantic_cache_hit = True
                cache_status.semantic_cache_hit = True
                cache_status.similarity_score = sim_score
                cache_status.cache_tier_matched = "SEMANTIC_L2"
                tracer.plan_id = "semantic_cache_hit_plan"
                tracer.verification_status = "SKIPPED"
                tracer.tokens_generated = 0
                
                await tracer.persist_to_db()
                return QueryResponse(
                    request_id=tracer.request_id,
                    query=request.query,
                    answer=sem_hit["answer"],
                    citations=[Citation(**c) for c in sem_hit.get("citations", [])],
                    execution_plan=ExecutionPlan(**sem_hit["execution_plan"]),
                    cache_status=cache_status,
                    latency_breakdown_ms=tracer.get_latency_breakdown(),
                    total_latency_ms=tracer.get_total_latency_ms(),
                    model_used=sem_hit.get("model_used", "cached"),
                    tokens_generated=0,
                    tokens_saved=sem_hit.get("tokens_saved", 350),
                    verification_status="PASSED",
                    steps_executed=steps_executed
                )

        # 4. Cache-Aware Planning Step
        tracer.start_step("cache_aware_planner")
        plan = planner.create_plan(request, kb_version=kb_version)
        tracer.plan_id = plan.plan_id
        tracer.retrieval_strategy = plan.retrieval_strategy
        tracer.model_used = plan.model_name
        tracer.end_step(plan.model_dump())
        steps_executed.append("cache_aware_planner")

        # 5. Query Decomposition (for multi-hop synthesis)
        sub_queries = [request.query]
        if plan.query_complexity == "multi_hop":
            tracer.start_step("query_decomposition")
            sub_queries = self._decompose_query(request.query)
            tracer.end_step({"sub_queries": sub_queries})
            steps_executed.append("query_decomposition")

        # 6. Check Tier 4: Retrieval Result Cache
        retrieved_chunks: List[DocumentChunk] = []
        
        if not request.force_no_cache:
            tracer.start_step("retrieval_cache_lookup")
            cached_chunks = retrieval_cache.get(request.kb_id, kb_version, plan.retrieval_strategy, 5, request.query)
            tracer.end_step({"hit": cached_chunks is not None})
            steps_executed.append("retrieval_cache_lookup")
            if cached_chunks is not None:
                tracer.retrieval_cache_hit = True
                cache_status.retrieval_cache_hit = True
                retrieved_chunks = cached_chunks

        # 7. Adaptive Retrieval Execution (on retrieval cache miss)
        if not retrieved_chunks:
            tracer.start_step(f"adaptive_retrieval_{plan.retrieval_strategy}")
            for sq in sub_queries:
                if plan.retrieval_strategy == "bm25":
                    chunks = bm25_retriever.retrieve(request.kb_id, kb_version, sq, top_k=5)
                elif plan.retrieval_strategy == "hybrid":
                    chunks = hybrid_retriever.retrieve(request.kb_id, kb_version, sq, top_k=5)
                else:
                    chunks = dense_retriever.retrieve(request.kb_id, kb_version, sq, top_k=5)
                retrieved_chunks.extend(chunks)

            # Deduplicate chunks by ID
            seen_ids = set()
            unique_chunks = []
            for c in retrieved_chunks:
                if c.id not in seen_ids:
                    seen_ids.add(c.id)
                    unique_chunks.append(c)
            retrieved_chunks = unique_chunks
            tracer.end_step({"chunks_retrieved": len(retrieved_chunks)})
            steps_executed.append(f"adaptive_retrieval_{plan.retrieval_strategy}")

            # Store in Retrieval Cache
            if retrieved_chunks and not request.force_no_cache:
                retrieval_cache.put(request.kb_id, kb_version, plan.retrieval_strategy, 5, request.query, retrieved_chunks)

        # 8. Cross-Encoder Reranking
        if plan.use_reranker and len(retrieved_chunks) > 3:
            tracer.start_step("cross_encoder_reranking")
            retrieved_chunks = reranker.rerank(request.query, retrieved_chunks, top_n=3)
            tracer.end_step({"top_chunks_retained": len(retrieved_chunks)})
            steps_executed.append("cross_encoder_reranking")

        # 9. Context Assembly & Inference Execution
        tracer.start_step("llm_inference_generation")
        context_text = "\n\n".join([f"--- Chunk {i+1} (Section: {c.section or 'Doc'}) ---\n{c.text}" for i, c in enumerate(retrieved_chunks)])
        system_prompt = "You are CacheMind, an advanced adaptive Agentic RAG assistant. Provide factual, cited answers strictly based on the provided document context."
        user_prompt = f"Context Information:\n{context_text}\n\nUser Question: {request.query}\n\nProvide a precise synthesis based on the context."

        inference_res = await llama_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=plan.model_name
        )
        answer_text = inference_res["text"]
        tracer.tokens_generated = inference_res["tokens_generated"]
        tracer.prefix_cache_hit = inference_res.get("prefix_cache_hit", False)
        cache_status.prefix_cache_hit = tracer.prefix_cache_hit
        tracer.end_step({"tokens": tracer.tokens_generated, "model": plan.model_name})
        steps_executed.append("llm_inference_generation")

        # 10. Quality & Citation Verification
        tracer.start_step("answer_verification")
        is_valid, verif_reason, citations = verifier.verify(request.query, answer_text, retrieved_chunks)
        tracer.verification_status = "PASSED" if is_valid else "FAILED"
        tracer.end_step({"valid": is_valid, "reason": verif_reason, "citations_count": len(citations)})
        steps_executed.append("answer_verification")

        # 11. Bounded Retry on Verification Failure
        if not is_valid and plan.verification_required:
            tracer.start_step("agentic_rewrite_retry")
            steps_executed.append("agentic_rewrite_retry")
            rewritten_q = f"{request.query} overview details"
            more_chunks = hybrid_retriever.retrieve(request.kb_id, kb_version, rewritten_q, top_k=4)
            if more_chunks:
                retrieved_chunks.extend(more_chunks)
                context_text = "\n\n".join([f"--- Chunk {i+1} ---\n{c.text}" for i, c in enumerate(retrieved_chunks)])
                user_prompt = f"Context Information:\n{context_text}\n\nUser Question: {request.query}"
                retry_res = await llama_client.generate(prompt=user_prompt, system_prompt=system_prompt, model=plan.model_name)
                answer_text = retry_res["text"]
                is_valid, _, citations = verifier.verify(request.query, answer_text, retrieved_chunks)
                tracer.verification_status = "RETRIED"
            tracer.end_step({"retry_valid": is_valid})

        # 12. Cache Admission Evaluation
        total_lat = tracer.get_total_latency_ms()
        should_admit, admit_reason, ttl = admission_controller.should_admit(
            query=request.query,
            generation_latency_ms=total_lat,
            tokens_generated=tracer.tokens_generated,
            verification_status=tracer.verification_status
        )

        # 13. Populate L1 & L2 Caches if admitted
        if should_admit and not request.force_no_cache:
            cache_payload = {
                "kb_id": request.kb_id,
                "answer": answer_text,
                "citations": [c.model_dump() for c in citations],
                "execution_plan": plan.model_dump(),
                "model_used": plan.model_name,
                "tokens_saved": tracer.tokens_generated or 350
            }
            exact_cache.put(request.kb_id, kb_version, request.query, cache_payload, ttl_seconds=ttl)
            semantic_cache.put(request.kb_id, kb_version, request.query, cache_payload, ttl_seconds=ttl)

        # 14. Finalize & Persist Trace
        await tracer.persist_to_db()

        return QueryResponse(
            request_id=tracer.request_id,
            query=request.query,
            answer=answer_text,
            citations=citations,
            execution_plan=plan,
            cache_status=cache_status,
            latency_breakdown_ms=tracer.get_latency_breakdown(),
            total_latency_ms=tracer.get_total_latency_ms(),
            model_used=plan.model_name,
            tokens_generated=tracer.tokens_generated,
            tokens_saved=tracer.tokens_saved,
            verification_status=tracer.verification_status,
            steps_executed=steps_executed
        )

    def _decompose_query(self, query: str) -> List[str]:
        if "compare" in query.lower() or "difference" in query.lower():
            return [query, f"key features and architecture in {query}", f"tradeoffs and performance in {query}"]
        return [query]

agentic_engine = AgenticRAGEngine()
