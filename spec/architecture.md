# Architecture

## System Overview

The Crime Statistics Analysis Agent is a full-stack application built around a specialized data-analysis agent graph. 

## Stack

- **Backend:** Python 3.11+, FastAPI (REST endpoints), LangGraph (Agent orchestration).
- **Frontend:** React via Vite with Vanilla CSS (Professional blue/white police dashboard theme).
- **Data Processing:** `pandas` for fast in-memory CSV operations (merging, cleaning, aggregating).
- **Database:** SQLite (local metadata, session, and conversation history storage).
- **LLM:** Gemini 1.5 (via `google-generativeai` or `langchain-google-genai`).
- **Observability:** `structlog` for structured request/response logging.

## Components & Data Flow

1. **Frontend (Vite/React):** 
   - Provides a drag-and-drop interface for CSV uploads.
   - Posts files to `/upload` API endpoint.
   - Provides a chat interface to post user queries to `/analyze` endpoint.
   - Renders structured dashboards (Executive Summary, Findings, Line/Bar Charts) from the API response.

2. **Backend (FastAPI):**
   - `/upload` endpoint parses CSVs, stores them temporarily (in-memory or temp disk), and extracts schemas.
   - `/analyze` endpoint takes a session ID and a user query, invoking the LangGraph agent.

3. **Agent (LangGraph):**
   - The graph orchestrates the reasoning.
   - The agent reads the user's query and the data schemas, determines the necessary Pandas aggregations, and generates Python code to query the data.
   - It executes the Pandas code safely (or uses predefined aggregation tools) and synthesizes the results into a structured JSON dashboard payload.

4. **Database (SQLite):**
   - Stores session mappings, conversational history, and pointers to temporary files.
