import os
import uuid
import pandas as pd
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from src.graph.agent import agentic_ai

router = APIRouter(prefix="/upload", tags=["upload"])

class UploadResponse(BaseModel):
    session_id: str
    files_processed: int
    schemas: dict[str, list[str]]

@router.post("", response_model=UploadResponse)
async def upload_files(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    
    session_id = str(uuid.uuid4())
    schemas = {}
    temp_paths = {}
    
    # Ensure temp directory exists
    temp_dir = os.path.join("data", "temp", session_id)
    os.makedirs(temp_dir, exist_ok=True)
    
    MAX_SIZE_BYTES = 4.5 * 1024 * 1024 # 4.5 MB (Vercel limit)
    total_size = 0
    
    for file in files:
        if not file.filename.endswith(".csv"):
            raise HTTPException(status_code=400, detail=f"File {file.filename} is not a CSV")
            
        content = await file.read()
        total_size += len(content)
        if total_size > MAX_SIZE_BYTES:
            raise HTTPException(status_code=413, detail="Total file size exceeds the 4.5MB Vercel serverless payload limit.")
            
        file_path = os.path.join(temp_dir, file.filename)
        with open(file_path, "wb") as f:
            f.write(content)
            
        try:
            # Fallback encoding to handle malicious/weird CSVs
            try:
                df = pd.read_csv(file_path, encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, encoding="latin1")
                
            if df.empty or len(df.columns) == 0:
                raise ValueError("CSV is empty or has no columns")
                
            schemas[file.filename] = list(df.columns)
            temp_paths[file.filename] = file_path
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse CSV {file.filename}: {str(e)}")
            
    # Initialize the LangGraph state for this session
    config = {"configurable": {"thread_id": session_id}}
    agentic_ai.update_state(config, {
        "csv_schemas": schemas,
        "temp_paths": temp_paths,
        "chat_history": []
    })
    
    return UploadResponse(
        session_id=session_id,
        files_processed=len(files),
        schemas=schemas
    )
