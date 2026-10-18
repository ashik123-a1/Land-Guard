"""LandGuard Complaints Router
Citizen grievance filing, status tracking, timeline inspection, and expedited review workflows.
"""

from typing import Optional
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse

from src.landguard_web.service import service
from src.landguard_web.dependencies import (
    templates,
    require_citizen_access,
    require_api_authenticated_user,
    require_api_admin_access,
)
from src.landguard_web.schemas import (
    CreateComplaintRequest,
    ExpediteRequestPayload,
    ExpediteDecisionPayload,
)

router = APIRouter(tags=["complaints"])


# ---------------------------------------------------------
# Citizen Complaint HTML Views
# ---------------------------------------------------------

@router.get("/user/complaints", response_class=HTMLResponse)
async def citizen_complaints(request: Request, status: Optional[str] = None):
    """Citizen complaints list and status tracking."""
    user = require_citizen_access(request)
    comps = service.list_complaints(user_id=user["user_id"], status=status)
    return templates.TemplateResponse(
        request=request,
        name="user/complaints.html",
        context={
            "current_user": user,
            "complaints": comps,
            "active_page": "complaints",
        },
    )


@router.get("/user/complaints/new", response_class=HTMLResponse)
async def citizen_complaint_new(
    request: Request,
    dag: Optional[str] = None,
    plot: Optional[str] = None,
    deed: Optional[str] = None,
):
    """File a new dispute grievance with optional expedited review request."""
    user = require_citizen_access(request)
    return templates.TemplateResponse(
        request=request,
        name="user/complaint_new.html",
        context={
            "current_user": user,
            "prefill_dag": dag or plot or "",
            "prefill_deed": deed or "",
            "active_page": "complaints",
        },
    )


@router.get("/user/complaints/{complaint_id}", response_class=HTMLResponse)
async def citizen_complaint_detail(request: Request, complaint_id: str):
    """Complaint progression timeline, investigator notes, and expedite status."""
    user = require_citizen_access(request)
    comp = service.get_complaint(complaint_id)
    if not comp:
        return RedirectResponse(url="/not-found", status_code=status.HTTP_303_SEE_OTHER)

    # IDOR Protection: Citizens can only view their own filed complaints; Admins have oversight
    if user.get("role") != "ADMIN" and comp.get("citizen_user_id") != user.get("user_id"):
        return RedirectResponse(url="/access-denied", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        request=request,
        name="user/complaint_detail.html",
        context={
            "current_user": user,
            "complaint": comp,
            "active_page": "complaints",
        },
    )


# ---------------------------------------------------------
# Complaints API Endpoints
# ---------------------------------------------------------

@router.get("/api/complaints")
async def api_list_complaints(request: Request, status: Optional[str] = None):
    """Returns citizen complaints. Requires authentication. Citizens only see their own; Admins see all."""
    user = require_api_authenticated_user(request)
    uid = user["user_id"] if user.get("role") == "CITIZEN" else None
    return service.list_complaints(user_id=uid, status=status)


@router.post("/api/complaints")
async def api_create_complaint(req: CreateComplaintRequest, request: Request):
    """Creates a new citizen grievance and links to investigation docket. Requires authentication."""
    user = require_api_authenticated_user(request)
    return service.create_complaint(user["user_id"], req.model_dump())


@router.get("/api/complaints/{complaint_id}")
async def api_get_complaint(complaint_id: str, request: Request):
    """Retrieves single complaint details. Requires authentication with IDOR protection."""
    user = require_api_authenticated_user(request)
    c = service.get_complaint(complaint_id)
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found.")
    if user.get("role") == "CITIZEN" and c.get("citizen_user_id") != user.get("user_id"):
        raise HTTPException(status_code=403, detail="Forbidden: You do not have permission to view this complaint.")
    return c


@router.post("/api/complaints/{complaint_id}/expedite")
async def api_request_expedite(complaint_id: str, req: ExpediteRequestPayload, request: Request):
    """Citizen requests expedited review on existing complaint with ownership verification."""
    user = require_api_authenticated_user(request)
    c = service.get_complaint(complaint_id)
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found.")
    if user.get("role") == "CITIZEN" and c.get("citizen_user_id") != user.get("user_id"):
        raise HTTPException(status_code=403, detail="Forbidden: You can only request expedited review for your own complaints.")
    try:
        return service.request_expedited_review(
            complaint_id,
            user_id=user["user_id"],
            reason=req.reason,
            reason_category=req.reason_category,
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@router.get("/api/complaints/{complaint_id}/ai-analysis")
@router.post("/api/complaints/{complaint_id}/ai-analysis")
async def api_complaint_ai_analysis(complaint_id: str, request: Request):
    """Generates preliminary AI claims extraction, duplicate detection, and registry evidence matching."""
    user = require_api_authenticated_user(request)
    c = service.get_complaint(complaint_id)
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found.")
    is_staff = user.get("role") in ["ADMIN", "INVESTIGATOR"]
    if not is_staff and c.get("citizen_user_id") != user.get("user_id"):
        raise HTTPException(status_code=403, detail="Forbidden: You do not have permission to view this complaint.")
    analysis = service.analyze_complaint_ai(
        complaint_id,
        viewer_user_id=user.get("user_id"),
        is_staff=is_staff,
    )
    if not analysis:
        raise HTTPException(status_code=500, detail="Failed to generate AI analysis for complaint.")
    return analysis


@router.post("/api/cases/{case_id}/expedite/decision")
async def api_decide_expedite(case_id: str, req: ExpediteDecisionPayload, request: Request):
    """Admin approves or rejects expedited review request. Requires Admin/Investigator."""
    user = require_api_admin_access(request)
    officer_name = user.get("full_name", "Senior Registrar M. Rahman")
    c = service.decide_expedite(case_id, decision=req.decision, reason=req.reason, officer=officer_name)
    if not c:
        raise HTTPException(status_code=404, detail="Case or complaint not found.")
    return c

