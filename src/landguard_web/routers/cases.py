"""LandGuard Cases Router
Investigator case docket, status updates, SLA tracking, officer notes, and clarification workflows.
"""

from typing import Optional
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

from src.landguard_web.service import service
from src.landguard_web.dependencies import (
    templates,
    require_admin_access,
    require_api_admin_access,
    require_api_authenticated_user,
)
from src.landguard_web.schemas import (
    CreateCaseRequest,
    UpdateCaseRequest,
    AddCaseNoteRequest,
    CaseClarificationRequest,
    CaseClarificationResponse,
)

router = APIRouter(tags=["cases"])


# ---------------------------------------------------------
# Admin Case HTML Views
# ---------------------------------------------------------

@router.get("/admin/cases", response_class=HTMLResponse)
async def admin_cases_list(request: Request, status: Optional[str] = None, priority: Optional[str] = None):
    """Investigation case docket."""
    user = require_admin_access(request)
    all_cases = service.list_cases(status=status, priority=priority)
    return templates.TemplateResponse(
        request=request,
        name="admin/cases.html",
        context={
            "current_user": user,
            "cases": all_cases,
            "active_page": "cases",
        },
    )


@router.get("/admin/cases/{case_id}", response_class=HTMLResponse)
async def admin_case_detail(request: Request, case_id: str):
    """Officer investigation workspace with priority changer, status transitions, and notes."""
    user = require_admin_access(request)
    c = service.get_case(case_id)
    if not c:
        return RedirectResponse(url="/not-found", status_code=status.HTTP_303_SEE_OTHER)

    sla = service.compute_case_sla(case_id)

    return templates.TemplateResponse(
        request=request,
        name="admin/case_detail.html",
        context={
            "current_user": user,
            "case": c,
            "sla": sla,
            "active_page": "cases",
        },
    )


# ---------------------------------------------------------
# Case API Endpoints
# ---------------------------------------------------------

@router.get("/api/cases")
async def list_cases(request: Request, status: Optional[str] = None, priority: Optional[str] = None):
    """Lists investigator review cases with optional status or priority filtering. Requires Admin/Investigator."""
    require_api_admin_access(request)
    return service.list_cases(status=status, priority=priority)


@router.post("/api/cases")
async def create_case(req: CreateCaseRequest, request: Request):
    """Creates a new investigator case with duplicate escalation check. Requires Admin/Investigator."""
    require_api_admin_access(request)
    if req.verification_id:
        existing = service.get_case_for_verification(req.verification_id)
        if existing:
            return JSONResponse(
                status_code=200,
                content={
                    **existing,
                    "is_duplicate": True,
                    "message": f"Dossier {req.verification_id} is already escalated under {existing.get('case_id')}."
                }
            )
    return service.create_case(req.model_dump())


@router.get("/api/cases/overdue")
async def get_overdue_cases_endpoint(request: Request):
    """Returns investigation cases exceeding SLA resolution deadlines. Requires Admin/Investigator."""
    require_api_admin_access(request)
    return service.get_overdue_cases()


@router.get("/api/cases/{case_id}")
async def get_case(case_id: str, request: Request):
    """Retrieves single case details. Requires Admin/Investigator."""
    require_api_admin_access(request)
    c = service.get_case(case_id)
    if not c:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")
    return c


@router.patch("/api/cases/{case_id}")
async def update_case(case_id: str, req: UpdateCaseRequest, request: Request):
    """Updates an existing investigation case. Requires Admin/Investigator."""
    require_api_admin_access(request)
    c = service.update_case(case_id, req.model_dump(exclude_unset=True))
    if not c:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")
    return c


@router.post("/api/cases/{case_id}/notes")
async def add_case_note(case_id: str, req: AddCaseNoteRequest, request: Request):
    """Appends an officer note to an investigation case. Requires Admin/Investigator."""
    user = require_api_admin_access(request)
    author = req.author or user.get("full_name", "Officer")
    c = service.add_case_note(case_id, note_text=req.note, author=author)
    if not c:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")
    return c


@router.post("/api/cases/{case_id}/clarification/request")
@router.post("/api/cases/{case_id}/clarifications")
async def request_case_clarification_endpoint(
    case_id: str,
    req: CaseClarificationRequest,
    request: Request,
):
    """Requests citizen clarification on a case, setting status to AWAITING_INFORMATION. Requires Admin/Investigator."""
    user = require_api_admin_access(request)
    c = service.request_case_clarification(
        case_id=case_id,
        question=req.question,
        officer_id=user["user_id"],
        officer_name=user.get("full_name", "Officer"),
    )
    if not c:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")
    return {
        "success": True,
        "case_id": case_id,
        "status": c.get("status"),
        "message": "Clarification request sent to citizen.",
    }


@router.post("/api/cases/{case_id}/clarification/respond")
@router.post("/api/cases/{case_id}/clarifications/{clarification_id}/respond")
async def respond_case_clarification_endpoint(
    case_id: str,
    req: CaseClarificationResponse,
    request: Request,
    clarification_id: Optional[str] = None,
):
    """Citizen submits clarification response, setting status back to UNDER_REVIEW.
    Strictly verifies ownership to prevent IDOR attacks between citizens.
    """
    user = require_api_authenticated_user(request)

    # 1. Resolve case (handling direct case_id or linked complaint_id)
    target_case = service.get_case(case_id)
    actual_case_id = case_id
    if not target_case:
        comp = service.get_complaint(case_id)
        if comp and comp.get("linked_case_id"):
            actual_case_id = comp["linked_case_id"]
            target_case = service.get_case(actual_case_id)

    if not target_case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")

    # 2. Strict IDOR authorization: Citizen can only respond to their own case
    if user.get("role") == "CITIZEN":
        user_id = user.get("user_id")
        is_owner = False

        # Check linked complaint ownership
        complaint_id = target_case.get("complaint_id")
        if complaint_id:
            comp = service.get_complaint(complaint_id)
            if comp and comp.get("citizen_user_id") == user_id:
                is_owner = True

        # Check linked verification ownership
        if not is_owner:
            verif_id = target_case.get("verification_id")
            if verif_id:
                verif = service.get_verification_record(verif_id)
                if verif and verif.get("user_id") == user_id:
                    is_owner = True

        # Check direct citizen_user_id on case record
        if not is_owner and target_case.get("citizen_user_id") == user_id:
            is_owner = True

        if not is_owner:
            raise HTTPException(
                status_code=403,
                detail="Forbidden: You are not authorized to respond to this investigation case.",
            )

    c = service.respond_case_clarification(
        case_id=actual_case_id,
        response_text=req.response,
        user_id=user["user_id"],
        user_name=user.get("full_name", "Citizen"),
        user_role=user.get("role"),
    )
    if not c:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")
    return {
        "success": True,
        "case_id": actual_case_id,
        "status": c.get("status"),
        "message": "Clarification response recorded successfully.",
    }


@router.post("/api/cases/sla/escalate")
async def trigger_sla_escalations_endpoint(request: Request):
    """Triggers an SLA evaluation sweep, producing real and idempotent escalation notes/notifications for overdue cases."""
    user = require_api_admin_access(request)
    escalated = service.process_sla_escalations()
    return {
        "success": True,
        "triggered_by": user.get("email"),
        "escalated_count": len(escalated),
        "escalated_cases": escalated,
    }

