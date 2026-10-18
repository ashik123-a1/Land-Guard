"""LandGuard Documents Router
Document ingestion, SHA-256 storage, bilingual OCR and CV analysis, file retrieval, and image streaming.
"""

import os
from fastapi import APIRouter, Request, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse

from src.landguard_web.service import service
from src.landguard_web.dependencies import (
    get_current_user,
    require_api_authenticated_user,
)

from src.landguard_web.rate_limiter import enforce_rate_limit

router = APIRouter(tags=["documents"])


@router.post("/api/upload")
async def upload_document(request: Request, file: UploadFile = File(...)):
    """
    Accepts synthetic deed document (.png, .jpg, .jpeg, .pdf), validates size and format,
    stores securely in data/uploads/deeds/<sha256>_<safe_name>, records in SQLite,
    runs bilingual OCR and CV checks, and returns extracted legal fields with uncertainty badges.
    Enforces rate limiting to prevent compute and storage exhaustion.
    """
    enforce_rate_limit(request, scope="document_upload", max_requests=15, window_seconds=60)
    filename = file.filename or "unknown_document.png"
    contents = await file.read()
    user = get_current_user(request)
    uid = user["user_id"] if user else "USR-CITIZEN-001"

    try:
        result = service.process_document_upload(contents, filename, uploaded_by=uid)
        return JSONResponse(status_code=200, content=result)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document processing failed: {str(e)}")


@router.get("/api/documents/{document_id}")
async def get_document_metadata(document_id: str, request: Request):
    """Retrieves document metadata from SQLite. Requires authentication and enforces ownership."""
    user = require_api_authenticated_user(request)
    doc = service.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found.")

    if user.get("role") == "CITIZEN" and doc.get("uploaded_by") and doc.get("uploaded_by") != user["user_id"]:
        raise HTTPException(status_code=403, detail="Forbidden: You can only access documents you uploaded.")

    return doc


@router.get("/api/documents/{document_id}/file")
async def get_document_file(document_id: str, request: Request):
    """Streams stored deed file securely. Requires authentication and enforces ownership."""
    user = require_api_authenticated_user(request)
    doc = service.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found.")

    if user.get("role") == "CITIZEN" and doc.get("uploaded_by") and doc.get("uploaded_by") != user["user_id"]:
        raise HTTPException(status_code=403, detail="Forbidden: You can only access documents you uploaded.")

    file_path = doc.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Physical document file missing from disk.")

    return FileResponse(file_path, media_type=doc.get("mime_type", "image/png"), filename=doc.get("filename"))


@router.post("/api/documents/{document_id}/reanalyze")
async def reanalyze_document_endpoint(document_id: str, request: Request):
    """Re-examines stored document by running bilingual OCR and CV anomaly detector on original file."""
    user = require_api_authenticated_user(request)
    doc = service.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found.")

    if user.get("role") == "CITIZEN" and doc.get("uploaded_by") and doc.get("uploaded_by") != user["user_id"]:
        raise HTTPException(status_code=403, detail="Forbidden: You can only reanalyze documents you uploaded.")

    reanalyzed = service.reanalyze_document(document_id)
    if not reanalyzed:
        raise HTTPException(status_code=500, detail="Failed to reanalyze stored document.")

    return reanalyzed


@router.delete("/api/documents/{document_id}")
async def delete_document_endpoint(document_id: str, request: Request):
    """Deletes or archives an uploaded document under statutory data retention policy. Enforces ownership and retention locks."""
    user = require_api_authenticated_user(request)
    is_admin = user.get("role") in ["ADMIN", "INVESTIGATOR"]
    try:
        result = service.delete_document(
            document_id=document_id,
            user_id=user["user_id"],
            is_admin=is_admin,
        )
        return result
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")


@router.get("/api/image/{filename}")
async def get_document_image(filename: str):

    """Serves document images securely from canonical images or temporary uploads."""
    clean_name = os.path.basename(filename)
    candidates = [
        os.path.join("data", "full", "images", clean_name),
        os.path.join("data", "targeted_expansion", "images", clean_name),
        os.path.join("data", "uploads", clean_name),
    ]
    for p in candidates:
        if os.path.exists(p):
            return FileResponse(p, media_type="image/png")
    raise HTTPException(status_code=404, detail="Image not found")
