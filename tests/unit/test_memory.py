import pytest
import os
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from src.graph.agent import agentic_ai
from src.graph.state import AgentState
from unittest.mock import patch, MagicMock

def test_memory_persists_across_turns():
    # Setup test DB
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    memory = SqliteSaver(conn)
    memory.setup()
    
    # Mock the LLM to just return a dummy script and then a dummy JSON response
    with patch("src.graph.nodes.LLMClient") as mock_client_cls:
        mock_instance = mock_client_cls.return_value
        # First turn mocks
        mock_instance.complete.side_effect = [
            "result = {'highest_crime': 'District A'}", # parse_intent
            '{"summary": "Initial summary", "findings": ["Finding 1"], "charts": [], "recommendations": []}', # synthesize_dashboard
            "result = {'drill_down': 'District A details'}", # parse_intent turn 2
            '{"summary": "Follow-up summary", "findings": ["Finding 2"], "charts": [], "recommendations": []}', # synthesize_dashboard turn 2
        ]
        mock_instance.provider_name = "mock"
        mock_instance.model = "mock"
        
        # We need a custom graph instance using the memory checkpointer
        from src.graph.agent import _build_graph
        with patch("src.graph.agent.get_settings") as mock_settings:
            mock_settings.return_value.database_url = "sqlite:///:memory:"
            # Recompile with memory checkpointer
            test_graph = _build_graph()
        
        config = {"configurable": {"thread_id": "test_session_123"}}
        
        # Turn 1
        initial_state = {
            "user_query": "What district has the most crime?",
            "csv_schemas": {"crimes": ["district", "date", "type"]},
            "temp_paths": {"crimes": "dummy.csv"}
        }
        
        # mock pandas reading
        with patch("pandas.read_csv", return_value=MagicMock()):
            final_1 = test_graph.invoke(initial_state, config=config)
            
        assert len(final_1["chat_history"]) == 2
        assert final_1["chat_history"][0]["role"] == "user"
        assert final_1["chat_history"][1]["role"] == "assistant"
        
        # Turn 2 - Follow up
        follow_up_state = {
            "user_query": "Drill down into that district."
        }
        
        with patch("pandas.read_csv", return_value=MagicMock()):
            final_2 = test_graph.invoke(follow_up_state, config=config)
            
        # The history should now have 4 messages because of the append operator in AgentState
        assert len(final_2["chat_history"]) == 4
        assert final_2["chat_history"][2]["role"] == "user"
        assert final_2["chat_history"][3]["role"] == "assistant"
        assert final_2["chat_history"][3]["content"] == "Follow-up summary"
