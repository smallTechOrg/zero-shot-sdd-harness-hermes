import pytest
from unittest.mock import patch, MagicMock
from src.capabilities.csv_nodes import csv_plan, csv_query, csv_execute, csv_explain
from src.capabilities.csv_state import CsvAgentState

# Mock LLMClient and load_prompt
@patch('src.capabilities.csv_nodes.LLMClient')
@patch('src.capabilities.csv_nodes.load_prompt')
def test_csv_plan(mock_load_prompt, mock_llm_client):
    # Setup mock
    mock_instance = MagicMock()
    mock_instance.complete.return_value = "SELECT * FROM table"
    mock_llm_client.return_value = mock_instance
    mock_load_prompt.return_value = "system prompt"

    state: CsvAgentState = {
        "input_text": "What is the total?",
        "schema_summary": {"tables": [{"table": "upload", "filename": "data.csv", "row_count": 10}]},
        "conversation_history": []
    }
    result = csv_plan(state)
    assert result["plan_text"] == "SELECT * FROM table"
    assert result["error"] is None

@patch('src.capabilities.csv_nodes.LLMClient')
@patch('src.capabilities.csv_nodes.load_prompt')
def test_csv_query(mock_load_prompt, mock_llm_client):
    mock_instance = MagicMock()
    mock_instance.complete.return_value = "SELECT COUNT(*) FROM upload"
    mock_llm_client.return_value = mock_instance
    mock_load_prompt.return_value = "system prompt"

    state: CsvAgentState = {
        "input_text": "What is the total?",
        "plan_text": "SELECT * FROM table",
        "schema_summary": {"tables": [{"table": "upload", "filename": "data.csv", "row_count": 10}]},
    }
    result = csv_query(state)
    assert result["generated_code"] == "SELECT COUNT(*) FROM upload"
    assert result["code_language"] == "sql"
    assert result["error"] is None

def test_csv_execute():
    # We'll mock duckdb in the execute_sql function; but for unit test we can mock execute_sql
    with patch('src.capabilities.csv_nodes.execute_sql') as mock_execute:
        mock_execute.return_value = ([{"col1": 1}], 10.0, "abc123")
        state: CsvAgentState = {
            "generated_code": "SELECT 1 as col1",
            "session_id": "test-session"
        }
        result = csv_execute(state)
        assert result["rows"] == [{"col1": 1}]
        assert result["row_count"] == 1
        assert result["latency_ms"] == 10.0
        assert result["result_hash"] == "abc123"
        assert result["error"] is None

@patch('src.capabilities.csv_nodes.LLMClient')
@patch('src.capabilities.csv_nodes.load_prompt')
def test_csv_explain(mock_load_prompt, mock_llm_client):
    mock_instance = MagicMock()
    mock_instance.complete.return_value = "This query counts rows."
    mock_llm_client.return_value = mock_instance
    mock_load_prompt.return_value = "system prompt"

    state: CsvAgentState = {
        "input_text": "What is the total?",
        "plan_text": "SELECT * FROM table",
        "generated_code": "SELECT COUNT(*) FROM upload",
        "rows": [{"count": 10}],
        "row_count": 10,
        "latency_ms": 12.5,
        "result_hash": "def456"
    }
    result = csv_explain(state)
    assert result["output_text"] == "This query counts rows."
    assert result["error"] is None