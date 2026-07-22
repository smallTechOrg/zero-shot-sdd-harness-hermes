from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

from src.api.upload import SESSION_FILES
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
    if req.session_id not in SESSION_FILES:
        raise HTTPException(status_code=404, detail="Session not found or expired")
        
    session_data = SESSION_FILES[req.session_id]
    
    # Run the graph
    initial_state: AgentState = {
        "run_id": "test-run",
        "session_id": req.session_id,
        "user_query": req.query,
        "csv_schemas": session_data["schemas"],
        "temp_paths": session_data["temp_paths"],
        "intermediate_results": {},
        "final_response": {}
    }
    
    try:
        final_state = agentic_ai.invoke(initial_state)
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
