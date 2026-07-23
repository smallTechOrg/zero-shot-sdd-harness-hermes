"""Graph nodes for Crime Statistics Analysis Agent."""
from __future__ import annotations

import json
import pandas as pd
from typing import Any

from src.graph.state import AgentState
from src.llm.client import LLMClient
from src.llm.providers.base import LLMError


def parse_intent(state: AgentState) -> AgentState:
    """LLM interprets the query and generates pandas code to extract insights."""
    try:
        client = LLMClient()
        system = (
            "You are a Python Data Analyst. You have a dictionary of pandas DataFrames called `dfs`.\n"
            "The keys are the filenames, and the values are the DataFrames.\n"
            "You must write a valid Python script that analyzes the data to answer the user query.\n"
            "Assign the final findings (a dictionary, string, or list) to a variable called `result`.\n"
            "If the user is asking a follow-up question, use the chat history to understand the context.\n"
            "DO NOT wrap your python code in markdown formatting like ```python, just output raw python code."
        )
        
        history_str = json.dumps(state.get("chat_history", [])[-4:], indent=2)
        user = (
            f"Chat History Context:\n{history_str}\n\n"
            f"New Query: {state['user_query']}\n"
            f"Schemas: {json.dumps(state['csv_schemas'], indent=2)}\n"
        )
        code = client.complete(system, user, max_tokens=1024).strip()
        if code.startswith("```python"):
            code = code[9:]
        if code.endswith("```"):
            code = code[:-3]
            
        return {
            "intermediate_results": {"code": code.strip()},
            "provider": client.provider_name,
            "model": client.model,
            "error": None,
        }
    except LLMError as exc:
        return {"error": str(exc)}


def execute_pandas(state: AgentState) -> AgentState:
    """Executes the generated pandas code."""
    if state.get("error"):
        return state
    
    code = state["intermediate_results"]["code"]
    temp_paths = state["temp_paths"]
    
    # Load dataframes
    dfs = {fname: pd.read_csv(path) for fname, path in temp_paths.items()}
    
    local_vars: dict[str, Any] = {"dfs": dfs, "pd": pd, "result": None}
    
    try:
        exec(code, {}, local_vars)
        result = local_vars.get("result")
        
        # Convert non-serializable pandas objects to basic python types
        if isinstance(result, (pd.DataFrame, pd.Series)):
            result = result.to_dict()
            
        return {
            "intermediate_results": {"code": code, "data": result},
            "error": None
        }
    except Exception as exc:
        return {"error": f"Pandas execution failed: {str(exc)}"}


def synthesize_dashboard(state: AgentState) -> AgentState:
    """Takes the raw data and creates a structured dashboard JSON."""
    if state.get("error"):
        # Fallback error response
        return {
            "final_response": {
                "summary": "An error occurred during analysis.",
                "findings": [state["error"]],
                "charts": [],
                "recommendations": []
            }
        }
        
    try:
        client = LLMClient()
        system = (
            "You are a Crime Analyst. Based on the user's query and the data results, "
            "synthesize a JSON dashboard payload with the following strict structure:\n"
            "{\n"
            "  \"summary\": \"Executive summary text\",\n"
            "  \"findings\": [\"insight 1\", \"insight 2\"],\n"
            "  \"charts\": [ { \"type\": \"bar\", \"title\": \"...\", \"labels\": [\"A\", \"B\"], \"datasets\": [{ \"label\": \"...\", \"data\": [1, 2] }] } ],\n"
            "  \"recommendations\": [\"action 1\"]\n"
            "}\n"
            "Output RAW JSON ONLY. No markdown."
        )
        
        history_str = json.dumps(state.get("chat_history", [])[-4:], indent=2)
        user = (
            f"Chat History Context:\n{history_str}\n\n"
            f"Query: {state['user_query']}\n"
            f"Data Results: {json.dumps(state['intermediate_results'].get('data', ''))}"
        )
        raw_json = client.complete(system, user, max_tokens=2048).strip()
        if raw_json.startswith("```json"):
            raw_json = raw_json[7:]
        if raw_json.endswith("```"):
            raw_json = raw_json[:-3]
            
        payload = json.loads(raw_json)
        
        new_history = [
            {"role": "user", "content": state["user_query"]},
            {"role": "assistant", "content": payload["summary"]}
        ]
        
        return {
            "final_response": payload,
            "chat_history": new_history,
            "status": "completed"
        }
    except Exception as exc:
        return {
            "final_response": {
                "summary": "Failed to synthesize JSON dashboard.",
                "findings": [str(exc)],
                "charts": [],
                "recommendations": []
            }
        }

def handle_error(state: AgentState) -> AgentState:
    return {"status": "failed"}

def finalize(state: AgentState) -> AgentState:
    return {"status": "completed"}
