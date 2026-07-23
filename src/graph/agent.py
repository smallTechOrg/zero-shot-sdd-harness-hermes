"""Graph assembly — StateGraph compiled once at import."""
from __future__ import annotations

from langgraph.graph import END, StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver

from src.graph.edges import after_parse, after_execute
from src.graph.nodes import parse_intent, execute_pandas, synthesize_dashboard, handle_error, finalize
from src.graph.state import AgentState
from src.config.settings import get_settings

def _build_graph():
    g = StateGraph(AgentState)
    g.add_node("parse_intent", parse_intent)
    g.add_node("execute_pandas", execute_pandas)
    g.add_node("synthesize_dashboard", synthesize_dashboard)
    g.add_node("handle_error", handle_error)
    g.add_node("finalize", finalize)
    
    g.set_entry_point("parse_intent")
    
    g.add_conditional_edges(
        "parse_intent",
        after_parse,
        {"execute_pandas": "execute_pandas", "handle_error": "handle_error"},
    )
    
    g.add_conditional_edges(
        "execute_pandas",
        after_execute,
        {"synthesize_dashboard": "synthesize_dashboard", "handle_error": "handle_error"},
    )
    
    g.add_edge("synthesize_dashboard", "finalize")
    g.add_edge("finalize", END)
    g.add_edge("handle_error", END)
    
    # Configure SqliteSaver
    db_url = get_settings().database_url
    # e.g., sqlite:///./data/app.db
    db_path = db_url.replace("sqlite:///", "")
    import sqlite3
    conn = sqlite3.connect(db_path, check_same_thread=False)
    memory = SqliteSaver(conn)
    memory.setup()
    
    return g.compile(checkpointer=memory)


agentic_ai = _build_graph()
