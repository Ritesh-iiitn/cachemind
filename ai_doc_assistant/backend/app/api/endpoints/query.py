from fastapi import APIRouter, HTTPException, status
from backend.app.models.schemas import QueryRequest, QueryResponse, ExecutionPlan
from backend.app.agents.graph import agentic_engine
from backend.app.agents.planner import planner
from backend.app.ingestion.service import ingestion_service

router = APIRouter()

@router.post("", response_model=QueryResponse)
async def execute_query(request: QueryRequest):
    """
    Execute query through Cache-Aware Planner and Agentic RAG engine.
    """
    try:
        response = await agentic_engine.execute_query(request)
        return response
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query execution error: {str(e)}")

@router.post("/plan", response_model=ExecutionPlan)
async def dry_run_plan(request: QueryRequest):
    """
    Dry-run execution planner to inspect cache routing, model selection,
    and complexity estimation without running full inference.
    """
    kb = await ingestion_service.get_kb(request.kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found.")
    return planner.create_plan(request, kb_version=kb.version)
