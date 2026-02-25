"""
upload.py — File Upload Endpoints

Handles Excel (.xlsx) and CSV (.csv) file uploads.
Saves the file, parses it, profiles the data, and returns a rich preview.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from app.config import settings
import os
import uuid

router = APIRouter()


@router.post("/")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload an Excel or CSV file for analysis.

    Returns:
        - file_id: unique identifier to reference this dataset later
        - filename: original filename
        - file_size_mb: size of the uploaded file
        - sheets: list of sheet names (for Excel; empty for CSV)
        - profile: rich column-level metadata (types, missing %, stats)
        - preview: first 10 rows as a list of dicts
    """
    # Validate file extension
    allowed_extensions = {".csv", ".xlsx", ".xls"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(allowed_extensions)}",
        )

    # Generate a unique ID for this upload
    file_id = str(uuid.uuid4())[:8]
    save_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}{ext}")

    # Save the file to disk
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    contents = await file.read()

    # Check file size
    size_mb = round(len(contents) / (1024 * 1024), 2)
    if size_mb > settings.MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({size_mb} MB). Maximum allowed: {settings.MAX_FILE_SIZE_MB} MB",
        )

    with open(save_path, "wb") as f:
        f.write(contents)

    # Parse and profile the file
    from app.core.file_parser import parse_file, profile_dataframe, get_sheet_names

    try:
        sheets = get_sheet_names(save_path)
        df = parse_file(save_path)
        profile = profile_dataframe(df)
    except Exception as e:
        # Clean up the saved file on parse failure
        if os.path.exists(save_path):
            os.remove(save_path)
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")

    # Build preview — convert to JSON-safe format
    import numpy as np
    import math

    preview_df = df.head(10).copy()
    # Convert datetime columns to strings for JSON serialization
    for col in preview_df.select_dtypes(include=["datetime64"]).columns:
        preview_df[col] = preview_df[col].astype(str)

    # Convert to records and sanitize NaN/Inf values (not JSON-compliant)
    preview_records = preview_df.to_dict(orient="records")
    for row in preview_records:
        for key, val in row.items():
            if val is None:
                continue
            if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                row[key] = None
            elif isinstance(val, (np.integer,)):
                row[key] = int(val)
            elif isinstance(val, (np.floating,)):
                if np.isnan(val) or np.isinf(val):
                    row[key] = None
                else:
                    row[key] = float(val)

    return {
        "file_id": file_id,
        "filename": file.filename,
        "file_size_mb": size_mb,
        "sheets": sheets,
        "profile": profile,
        "preview": preview_records,
    }


@router.get("/list")
async def list_uploads():
    """List all previously uploaded files."""
    upload_dir = settings.UPLOAD_DIR
    if not os.path.exists(upload_dir):
        return {"files": []}

    files = []
    for fname in os.listdir(upload_dir):
        if fname.startswith("."):
            continue
        path = os.path.join(upload_dir, fname)
        files.append({
            "filename": fname,
            "size_mb": round(os.path.getsize(path) / (1024 * 1024), 2),
        })
    return {"files": files}


@router.delete("/{file_id}")
async def delete_upload(file_id: str):
    """Delete a previously uploaded file."""
    from app.core.file_parser import get_file_path
    try:
        path = get_file_path(file_id, settings.UPLOAD_DIR)
        os.remove(path)
        return {"status": "deleted", "file_id": file_id}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {file_id}")
