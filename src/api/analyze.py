from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

from src.graph.agent import agentic_ai
from src.graph.state import AgentState

router = APIRouter(prefix="/analyze", tags=["analyze"])

class AnalyzeRequest(BaseModel):
    session_id: str
    query: str

class ChartData(BaseModel):
    type: str
    title: str
    labels: List[str]
    datasets: List[Dict[str, Any]]

class AnalyzeResponse(BaseModel):
    summary: str
    findings: List[str]
    charts: List[ChartData]
    recommendations: List[str]

@router.post("", response_model=AnalyzeResponse)
async def analyze_query(req: AnalyzeRequest):
    config = {"configurable": {"thread_id": req.session_id}}
    
    # Retrieve current state to check if session exists
    current_state = agentic_ai.get_state(config)
    if not current_state or not current_state.values.get("csv_schemas"):
        raise HTTPException(status_code=404, detail="Session not found or expired")
        
    try:
        # We only need to provide the updated parts of the state.
        # The checkpointer restores the rest (schemas, paths, history).
        final_state = agentic_ai.invoke({"user_query": req.query}, config=config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")
        
    if final_state.get("error") and not final_state.get("final_response"):
        raise HTTPException(status_code=500, detail=final_state["error"])
        
    response_data = final_state.get("final_response", {})
    
    # Ensure it matches the schema closely
    return AnalyzeResponse(
        summary=response_data.get("summary", "No summary generated."),
        findings=response_data.get("findings", []),
        charts=response_data.get("charts", []),
        recommendations=response_data.get("recommendations", [])
    )
