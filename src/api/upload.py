import os
import uuid
import pandas as pd
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/upload", tags=["upload"])

class UploadResponse(BaseModel):
    session_id: str
    files_processed: int
    schemas: dict[str, list[str]]

# In-memory store for Phase 1. (Phase 2 will use SQLite)
SESSION_FILES = {}

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
    
    for file in files:
        if not file.filename.endswith(".csv"):
            raise HTTPException(status_code=400, detail=f"File {file.filename} is not a CSV")
            
        file_path = os.path.join(temp_dir, file.filename)
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
            
        try:
            df = pd.read_csv(file_path)
            schemas[file.filename] = list(df.columns)
            temp_paths[file.filename] = file_path
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse CSV {file.filename}: {str(e)}")
            
    SESSION_FILES[session_id] = {
        "schemas": schemas,
        "temp_paths": temp_paths
    }
    
    return UploadResponse(
        session_id=session_id,
        files_processed=len(files),
        schemas=schemas
    )
