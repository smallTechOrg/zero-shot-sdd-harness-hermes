# Agent Graph

## Pattern: ReAct / Plan-and-Execute

The agent operates on a ReAct (Reason + Act) loop augmented for data analysis.

## State
The graph state (`GraphState`) includes:
- `session_id`: Current session identifier.
- `chat_history`: Conversation history.
- `user_query`: The latest query.
- `csv_schemas`: Extracted column info.
- `intermediate_results`: Data aggregation results.
- `final_response`: The structured dashboard payload.

## Nodes

1. **`parse_intent`**: LLM interprets the user query against the `csv_schemas`. It decides what aggregations/group-bys are needed.
2. **`execute_pandas`**: (Tool Node) A controlled execution environment where `pandas` operations are run on the uploaded CSV data based on the LLM's instructions.
3. **`synthesize_dashboard`**: LLM takes the raw `intermediate_results` and formats them into a structured JSON response (Summary, Findings, Charts Data, Recommendations).

## Edges
- Entry -> `parse_intent`
- `parse_intent` -> `execute_pandas` (if data fetch is needed)
- `execute_pandas` -> `synthesize_dashboard`
- `synthesize_dashboard` -> END

## Error Handling
If `execute_pandas` fails (e.g., column not found), it returns the error back to `parse_intent` to retry up to 2 times before falling back to a graceful error message in `synthesize_dashboard`.

## Concurrency
Isolated by `session_id`. Each request processes its own in-memory data copies.
