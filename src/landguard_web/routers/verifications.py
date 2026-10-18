"""LandGuard Verifications Router
Citizen multi-step verification wizard, verification dossier views, official registrar determination, and core verification API.
"""

from typing import Optional
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

from src.landguard_web.service import service
from src.landguard_web.dependencies import (
    templates,
    get_current_user,
    require_citizen_access,
    require_admin_access,
)
from src.landguard_web.schemas import (
    VerifyRequest,
    VerificationDecisionRequest,
)

router = APIRouter(tags=["verifications"])


# ---------------------------------------------------------
# Citizen Verification HTML Views
# ---------------------------------------------------------

@router.get("/user/verify", response_class=HTMLResponse)
@router.get("/user/verify/new", response_class=HTMLResponse)
async def citizen_verify_stepper(request: Request):
    """Citizen multi-step verification wizard (Ingestion, Extraction, Confirmation, Findings)."""
    user = require_citizen_access(request)
    return templates.TemplateResponse(
        request=request,
        name="user/verify.html",
        context={
            "current_user": user,
            "sample_cases": service.get_sample_cases(),
            "active_page": "verify",
        },
    )


@router.get("/user/verify/{verification_id}", response_class=HTMLResponse)
async def citizen_verify_detail(request: Request, verification_id: str):
    """Displays specific verification findings and evidence report.
    Enforces IDOR ownership protection for citizens while allowing authorized staff review.
    """
    user = require_citizen_access(request)
    rec = service.get_verification_record(verification_id)
    if not rec:
        return RedirectResponse(url="/not-found", status_code=status.HTTP_303_SEE_OTHER)

    # Enforce IDOR protection: A citizen cannot inspect another citizen's private dossier
    if user.get("role") == "CITIZEN" and rec.get("user_id") and rec.get("user_id") != user["user_id"]:
        return RedirectResponse(url="/access-denied", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        request=request,
        name="user/verify_detail.html",
        context={
            "current_user": user,
            "verification": rec,
            "active_page": "history",
        },
    )


# ---------------------------------------------------------
# Admin Verification HTML Views
# ---------------------------------------------------------

@router.get("/admin/verifications", response_class=HTMLResponse)
async def admin_verifications(request: Request, status: Optional[str] = None):
    """Verification queue with status filtering."""
    user = require_admin_access(request)
    history = service.get_audit_history()
    if status and status.upper() != "ALL":
        history = [v for v in history if v.get("overall_status") == status.upper()]

    return templates.TemplateResponse(
        request=request,
        name="admin/verifications.html",
        context={
            "current_user": user,
            "verifications": history,
            "active_page": "verifications",
        },
    )


@router.get("/admin/verifications/{verification_id}", response_class=HTMLResponse)
async def admin_verification_detail(request: Request, verification_id: str):
    """Investigator review workspace for a single verification dossier."""
    user = require_admin_access(request)
    rec = service.get_verification_record(verification_id)
    if not rec:
        return RedirectResponse(url="/not-found", status_code=status.HTTP_303_SEE_OTHER)

    existing_case = service.get_case_for_verification(verification_id)

    return templates.TemplateResponse(
        request=request,
        name="admin/verification_detail.html",
        context={
            "current_user": user,
            "verification": rec,
            "existing_case": existing_case,
            "active_page": "verifications",
        },
    )


# ---------------------------------------------------------
# Verification API Endpoints
# ---------------------------------------------------------

@router.get("/api/samples")
@router.get("/api/sample-cases")
async def list_sample_cases():
    """Returns the list of curated demo cases for instant one-click testing."""
    return service.get_sample_cases()


from src.landguard_web.rate_limiter import enforce_rate_limit

@router.post("/api/verify")
async def verify_record(req: VerifyRequest, request: Request):
    """
    Evaluates confirmed legal fields against Cadastral Registry,
    runs deterministic statutory rules, XGBoost inference, and CV anomaly checks.
    Enforces rate limiting to prevent compute exhaustion.
    """
    enforce_rate_limit(request, scope="verification", max_requests=20, window_seconds=60)
    try:
        confirmed = dict(req.confirmed_fields)
        if req.document_type and "document_type" not in confirmed:
            confirmed["document_type"] = req.document_type
        
        user = get_current_user(request)
        if user and user.get("user_id"):
            confirmed["user_id"] = user["user_id"]
        else:
            confirmed["user_id"] = "USR-CITIZEN-001"

        result = service.verify_transaction(
            confirmed_fields=confirmed,
            image_path=req.image_path,
            original_ocr_fields=req.original_ocr_fields,
            evidence_source=req.evidence_source,
        )
        return JSONResponse(status_code=200, content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")


@router.post("/api/verifications/{verification_id}/decision")
async def api_record_verification_decision(verification_id: str, req: VerificationDecisionRequest, request: Request):
    """
    Authorized Registrar / Investigator records an official determination on a verification dossier.
    Enforces RBAC: rejects unauthenticated or CITIZEN role requests.
    Persists decision and statutory reasons to record and logs an immutable audit event in SQLite.
    """
    user = get_current_user(request)
    if not user or user.get("role") == "CITIZEN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only authorized investigators and registrars may record formal determinations."
        )

    if not req.reason or not req.reason.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Statutory justification and notes are required to record a formal determination."
        )

    officer_name = user.get("full_name", "Investigator")
    user_id = user.get("user_id", "USR-OFFICER-001")

    try:
        det = service.record_verification_decision(
            verification_id=verification_id,
            decision=req.decision,
            reason=req.reason,
            user_id=user_id,
            officer_name=officer_name,
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

    if not det:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Verification dossier '{verification_id}' not found.")

    return {
        "success": True,
        "verification_id": verification_id,
        "determination": det,
        "message": f"Official determination '{req.decision}' recorded successfully."
    }
