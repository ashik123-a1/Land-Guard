"""LandGuard FastAPI Web Application
Provides interactive browser UI, login-first authentication, separate Citizen and Admin portals,
document upload, bilingual OCR extraction, cadastral registry verification, ML & CV supplementary evidence,
docket case management, and immutable audit logs.
"""

import os
import io
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Response, Depends, status
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from src.landguard_web.service import LandGuardVerificationService

app = FastAPI(
    title="LandGuard AI Land Record Verification",
    description="Statutory land deed verification, bilingual OCR, and multi-modal risk assessment.",
    version="2.0.0",
)

service = LandGuardVerificationService()

templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)


# ---------------------------------------------------------
# Request Models
# ---------------------------------------------------------

class LoginRequest(BaseModel):
    email: str
    password: str
    redirect: Optional[str] = None


class VerifyRequest(BaseModel):
    confirmed_fields: Dict[str, Any] = Field(..., description="User-reviewed legal deed fields")
    image_path: Optional[str] = Field(None, description="Path or identifier of uploaded document image")
    original_ocr_fields: Optional[Dict[str, Any]] = Field(None, description="Original unedited OCR fields for diff audit")


class CreateCaseRequest(BaseModel):
    title: Optional[str] = None
    deed_number: Optional[str] = "N/A"
    dag_plot_number: Optional[str] = "N/A"
    verification_id: Optional[str] = None
    priority: Optional[str] = "HIGH"
    assigned_officer: Optional[str] = "Unassigned"
    statutory_finding: Optional[str] = "REVIEW_REQUIRED"
    ml_risk_score: Optional[float] = None
    evidence_summary: Optional[str] = ""
    initial_note: Optional[str] = "Case initialized from LandGuard verification finding."


class UpdateCaseRequest(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_officer: Optional[str] = None
    evidence_summary: Optional[str] = None
    title: Optional[str] = None


class AddCaseNoteRequest(BaseModel):
    note: str
    author: Optional[str] = "Officer"


class CreateComplaintRequest(BaseModel):
    category: str
    dag_plot_number: str
    deed_number: str
    title: str
    narrative_description: str
    is_expedited: Optional[bool] = False
    expedite_reason: Optional[str] = None


class ExpediteRequestPayload(BaseModel):
    reason: str


class ExpediteDecisionPayload(BaseModel):
    decision: str
    reason: str


# ---------------------------------------------------------
# Authentication & Role Authorization Helpers
# ---------------------------------------------------------

def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """Resolves active user from HTTP session cookie or Authorization header."""
    session_id = request.cookies.get("landguard_session")
    if not session_id:
        auth_hdr = request.headers.get("Authorization")
        if auth_hdr and auth_hdr.startswith("Bearer "):
            session_id = auth_hdr.split(" ")[1]

    if not session_id:
        return None
    return service.get_user_by_session(session_id)


def require_authenticated_user(request: Request) -> Dict[str, Any]:
    """Ensures user has an active session, or redirects to /login."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": f"/login?redirect={request.url.path}"}
        )
    return user


def require_citizen_access(request: Request) -> Dict[str, Any]:
    """Citizen portal guard: ensures authenticated user is citizen or admin."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": f"/login?redirect={request.url.path}"}
        )
    return user


def require_admin_access(request: Request) -> Dict[str, Any]:
    """Admin / Investigator portal guard: denies CITIZEN role with 403 / access-denied."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": f"/login?redirect={request.url.path}"}
        )
    if user.get("role") == "CITIZEN":
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/access-denied"}
        )
    return user


# ---------------------------------------------------------
# Public Routes (Landing, Login, Access-Denied, Not-Found)
# ---------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """
    Public Landing / Welcome Page.
    Introduces the LandGuard P3 platform, capabilities, and synthetic data disclosures.
    """
    user = get_current_user(request)
    return templates.TemplateResponse(
        request=request,
        name="public/landing.html",
        context={
            "current_user": user,
            "banner_text": "SYNTHETIC DEMO — NOT AN OFFICIAL DOCUMENT",
        },
    )


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, redirect: Optional[str] = None):
    """
    Login Screen with username/password form and 3 one-click Demo Role buttons.
    If already authenticated, redirects directly to role portal.
    """
    user = get_current_user(request)
    if user:
        if user.get("role") == "CITIZEN":
            return RedirectResponse(url=redirect or "/user/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        else:
            return RedirectResponse(url=redirect or "/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        request=request,
        name="public/login.html",
        context={"redirect_target": redirect or ""},
    )


@app.get("/access-denied", response_class=HTMLResponse)
async def access_denied_page(request: Request):
    """Displays 403 Forbidden Access Denied screen when a citizen attempts an admin route."""
    user = get_current_user(request)
    return templates.TemplateResponse(
        request=request,
        name="public/access_denied.html",
        context={"current_user": user},
    )


@app.get("/not-found", response_class=HTMLResponse)
async def not_found_page(request: Request):
    """Displays 404 page."""
    return templates.TemplateResponse(
        request=request,
        name="public/not_found.html",
        context={},
    )


@app.get("/logout")
async def logout(request: Request):
    """Terminates session, clears cookie, and redirects to /login."""
    session_id = request.cookies.get("landguard_session")
    if session_id:
        service.destroy_session(session_id)
    resp = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    resp.delete_cookie("landguard_session")
    return resp


# ---------------------------------------------------------
# Auth API Endpoints
# ---------------------------------------------------------

@app.post("/api/auth/login")
async def api_login(req: LoginRequest, response: Response):
    """Authenticates email and password, creates session, and sets cookie."""
    user = service.authenticate_user(req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    session_id = service.create_session(user)
    target = req.redirect
    if not target or target.strip() == "":
        target = "/user/dashboard" if user.get("role") == "CITIZEN" else "/admin/dashboard"

    res = JSONResponse(content={"success": True, "redirect_url": target, "user": user})
    res.set_cookie(
        key="landguard_session",
        value=session_id,
        httponly=True,
        samesite="lax",
        max_age=86400,
    )
    return res


@app.post("/api/auth/demo-login")
async def api_demo_login(role: str = "citizen"):
    """One-click demonstration role entry for hackathon testing."""
    role_map = {
        "citizen": "citizen@landguard.gov.bd",
        "investigator": "investigator@landguard.gov.bd",
        "admin": "admin@landguard.gov.bd",
    }
    email = role_map.get(role.lower())
    if not email or email not in service.users:
        raise HTTPException(status_code=400, detail="Invalid demo role.")

    user = dict(service.users[email])
    user.pop("password", None)
    session_id = service.create_session(user)

    target = "/user/dashboard" if user.get("role") == "CITIZEN" else "/admin/dashboard"
    res = JSONResponse(content={"success": True, "redirect_url": target, "user": user})
    res.set_cookie(
        key="landguard_session",
        value=session_id,
        httponly=True,
        samesite="lax",
        max_age=86400,
    )
    return res


@app.post("/api/auth/logout")
async def api_logout(request: Request):
    """Terminates session on logout."""
    session_id = request.cookies.get("landguard_session")
    if session_id:
        service.destroy_session(session_id)
    res = JSONResponse(content={"success": True, "message": "Logged out."})
    res.delete_cookie("landguard_session")
    return res


@app.get("/api/auth/me")
async def api_auth_me(request: Request):
    """Returns currently authenticated user profile."""
    user = get_current_user(request)
    if not user:
        return {"authenticated": False, "user": None}
    return {"authenticated": True, "user": user}


# ---------------------------------------------------------
# Citizen / User Portal Routes (/user/*)
# ---------------------------------------------------------

@app.get("/user/dashboard", response_class=HTMLResponse)
async def citizen_dashboard(request: Request):
    """Citizen Dashboard: Digital Identity Card, stats, quick action, and recent items."""
    user = require_citizen_access(request)
    dash_data = service.get_citizen_dashboard(user["user_id"])
    return templates.TemplateResponse(
        request=request,
        name="user/dashboard.html",
        context={
            "current_user": user,
            "data": dash_data,
            "active_page": "dashboard",
        },
    )


@app.get("/user/verify", response_class=HTMLResponse)
@app.get("/user/verify/new", response_class=HTMLResponse)
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


@app.get("/user/verify/{verification_id}", response_class=HTMLResponse)
async def citizen_verify_detail(request: Request, verification_id: str):
    """Displays specific verification findings and evidence report."""
    user = require_citizen_access(request)
    rec = service.get_verification_record(verification_id)
    if not rec:
        return RedirectResponse(url="/not-found", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        request=request,
        name="user/verify_detail.html",
        context={
            "current_user": user,
            "verification": rec,
            "active_page": "history",
        },
    )


@app.get("/user/parcels", response_class=HTMLResponse)
async def citizen_parcels(request: Request, q: str = ""):
    """Cadastral Registry search and listing."""
    user = require_citizen_access(request)
    parcels = service.search_parcels(query=q, limit=25)
    return templates.TemplateResponse(
        request=request,
        name="user/parcels.html",
        context={
            "current_user": user,
            "parcels": parcels,
            "query": q,
            "total_parcels": len(service.parcels_by_plot),
            "active_page": "parcels",
        },
    )


@app.get("/user/parcels/{plot_or_id}", response_class=HTMLResponse)
async def citizen_parcel_detail(request: Request, plot_or_id: str):
    """Detailed parcel profile with CS -> SA -> RS -> BS survey chain, deed history, and tax."""
    user = require_citizen_access(request)
    details = service.get_parcel_details(plot_or_id)
    if not details:
        return RedirectResponse(url="/not-found", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        request=request,
        name="user/parcel_detail.html",
        context={
            "current_user": user,
            "parcel": details["parcel"],
            "chain_of_title": details["chain_of_title"],
            "history_transactions": details["history_transactions"],
            "mutations": details["mutations"],
            "tax_status": details["tax_status"],
            "active_page": "parcels",
        },
    )


@app.get("/user/history", response_class=HTMLResponse)
async def citizen_history(request: Request):
    """Citizen's past verification submissions with status badges and report downloads."""
    user = require_citizen_access(request)
    history = service.get_audit_history()
    return templates.TemplateResponse(
        request=request,
        name="user/history.html",
        context={
            "current_user": user,
            "history": history,
            "active_page": "history",
        },
    )


@app.get("/user/complaints", response_class=HTMLResponse)
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


@app.get("/user/complaints/new", response_class=HTMLResponse)
async def citizen_complaint_new(request: Request, dag: Optional[str] = None, deed: Optional[str] = None):
    """File a new dispute grievance with optional expedited review request."""
    user = require_citizen_access(request)
    return templates.TemplateResponse(
        request=request,
        name="user/complaint_new.html",
        context={
            "current_user": user,
            "prefill_dag": dag or "",
            "prefill_deed": deed or "",
            "active_page": "complaints",
        },
    )


@app.get("/user/complaints/{complaint_id}", response_class=HTMLResponse)
async def citizen_complaint_detail(request: Request, complaint_id: str):
    """Complaint progression timeline, investigator notes, and expedite status."""
    user = require_citizen_access(request)
    comp = service.get_complaint(complaint_id)
    if not comp:
        return RedirectResponse(url="/not-found", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        request=request,
        name="user/complaint_detail.html",
        context={
            "current_user": user,
            "complaint": comp,
            "active_page": "complaints",
        },
    )


@app.get("/user/notifications", response_class=HTMLResponse)
async def citizen_notifications(request: Request):
    """Notification alerts list."""
    user = require_citizen_access(request)
    notifs = service.get_notifications(user["user_id"])
    return templates.TemplateResponse(
        request=request,
        name="user/notifications.html",
        context={
            "current_user": user,
            "notifications": notifs,
            "active_page": "notifications",
        },
    )


@app.get("/user/profile", response_class=HTMLResponse)
async def citizen_profile(request: Request):
    """Citizen profile and full Digital Identity Card."""
    user = require_citizen_access(request)
    return templates.TemplateResponse(
        request=request,
        name="user/profile.html",
        context={
            "current_user": user,
            "user": user,
            "active_page": "profile",
        },
    )


@app.get("/user/settings", response_class=HTMLResponse)
async def citizen_settings(request: Request):
    """Citizen preferences."""
    user = require_citizen_access(request)
    return templates.TemplateResponse(
        request=request,
        name="user/settings.html",
        context={
            "current_user": user,
            "active_page": "settings",
        },
    )


# ---------------------------------------------------------
# Admin / Investigator Portal Routes (/admin/*)
# ---------------------------------------------------------

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Investigator / Admin Command Center with Bento-grid metrics, expedite queue, and recent alerts."""
    user = require_admin_access(request)
    stats = service.get_dashboard_stats()
    analytics = service.get_admin_dashboard_analytics(year="2026")
    all_cases = service.list_cases()
    history = service.get_audit_history()

    pending_expedites = [c for c in service.complaints.values() if c.get("expedite_status") == "PENDING_DECISION"]
    review_queue_count = len([v for v in history if v.get("overall_status") in ["CONFIRMED_INCONSISTENCY", "REVIEW_REQUIRED"]])
    inconsistencies_count = len([v for v in history if v.get("overall_status") == "CONFIRMED_INCONSISTENCY"])

    return templates.TemplateResponse(
        request=request,
        name="admin/dashboard.html",
        context={
            "current_user": user,
            "stats": stats,
            "analytics": analytics,
            "cases": all_cases[:6],
            "recent_verifications": history[:6],
            "pending_expedites": pending_expedites,
            "review_queue_count": review_queue_count,
            "inconsistencies_count": inconsistencies_count,
            "active_page": "dashboard",
        },
    )


@app.get("/admin/verifications", response_class=HTMLResponse)
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


@app.get("/admin/verifications/{verification_id}", response_class=HTMLResponse)
async def admin_verification_detail(request: Request, verification_id: str):
    """Investigator review workspace for a single verification dossier."""
    user = require_admin_access(request)
    rec = service.get_verification_record(verification_id)
    if not rec:
        return RedirectResponse(url="/not-found", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        request=request,
        name="admin/verification_detail.html",
        context={
            "current_user": user,
            "verification": rec,
            "active_page": "verifications",
        },
    )


@app.get("/admin/cases", response_class=HTMLResponse)
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


@app.get("/admin/cases/{case_id}", response_class=HTMLResponse)
async def admin_case_detail(request: Request, case_id: str):
    """Officer investigation workspace with priority changer, status transitions, and notes."""
    user = require_admin_access(request)
    c = service.get_case(case_id)
    if not c:
        return RedirectResponse(url="/not-found", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        request=request,
        name="admin/case_detail.html",
        context={
            "current_user": user,
            "case": c,
            "active_page": "cases",
        },
    )


@app.get("/admin/parcels", response_class=HTMLResponse)
async def admin_parcels(request: Request, q: str = ""):
    """Admin Cadastral Explorer."""
    user = require_admin_access(request)
    parcels = service.search_parcels(query=q, limit=25)
    return templates.TemplateResponse(
        request=request,
        name="admin/parcels.html",
        context={
            "current_user": user,
            "parcels": parcels,
            "query": q,
            "total_parcels": len(service.parcels_by_plot),
            "active_page": "parcels",
        },
    )


@app.get("/admin/reports", response_class=HTMLResponse)
async def admin_reports(request: Request):
    """Evidence dossiers list with SHA-256 certificate hashes."""
    user = require_admin_access(request)
    history = service.get_audit_history()
    generated_reports = []
    for h in history:
        rep = service.generate_report(h["verification_id"])
        if rep:
            generated_reports.append(rep)

    return templates.TemplateResponse(
        request=request,
        name="admin/reports.html",
        context={
            "current_user": user,
            "reports": generated_reports,
            "active_page": "reports",
        },
    )


@app.get("/admin/reports/{verification_id}", response_class=HTMLResponse)
async def admin_report_detail(request: Request, verification_id: str):
    """Official printable Evidence Dossier Certificate."""
    user = require_admin_access(request)
    rep = service.generate_report(verification_id)
    if not rep:
        return RedirectResponse(url="/not-found", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        request=request,
        name="admin/report_detail.html",
        context={"report": rep},
    )


@app.get("/admin/analytics", response_class=HTMLResponse)
async def admin_analytics(request: Request):
    """Analytics and metrics."""
    user = require_admin_access(request)
    return templates.TemplateResponse(
        request=request,
        name="admin/analytics.html",
        context={
            "current_user": user,
            "active_page": "analytics",
        },
    )


@app.get("/admin/audit", response_class=HTMLResponse)
async def admin_audit(request: Request):
    """Immutable audit trail."""
    user = require_admin_access(request)
    audit_events = service.get_audit_trail(limit=50)
    return templates.TemplateResponse(
        request=request,
        name="admin/audit.html",
        context={
            "current_user": user,
            "audit_events": audit_events,
            "active_page": "audit",
        },
    )


@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users(request: Request):
    """User directory and RBAC assignments."""
    user = require_admin_access(request)
    users = service.list_users()
    return templates.TemplateResponse(
        request=request,
        name="admin/users.html",
        context={
            "current_user": user,
            "users": users,
            "active_page": "users",
        },
    )


@app.get("/admin/models", response_class=HTMLResponse)
async def admin_models(request: Request):
    """AI Model Governance card."""
    user = require_admin_access(request)
    return templates.TemplateResponse(
        request=request,
        name="admin/models.html",
        context={
            "current_user": user,
            "active_page": "models",
        },
    )


@app.get("/admin/system", response_class=HTMLResponse)
async def admin_system(request: Request):
    """System health and infrastructure diagnostics."""
    user = require_admin_access(request)
    return templates.TemplateResponse(
        request=request,
        name="admin/system.html",
        context={
            "current_user": user,
            "db_type": service.db.db_type,
            "active_page": "system",
        },
    )


@app.get("/admin/settings", response_class=HTMLResponse)
async def admin_settings(request: Request):
    """Operations settings and SLA."""
    user = require_admin_access(request)
    return templates.TemplateResponse(
        request=request,
        name="admin/settings.html",
        context={
            "current_user": user,
            "active_page": "settings",
        },
    )


# ---------------------------------------------------------
# Core Verification & Operational API Endpoints
# ---------------------------------------------------------

@app.get("/api/health")
async def health_check():
    """Health check endpoint indicating model readiness, active database, and standby configuration."""
    neon_status = "STANDBY" if service.db.neon_configured else "NOT_CONFIGURED"
    return {
        "status": "HEALTHY",
        "service": "LandGuard AI Land Record Verification",
        "version": "2.0.0",
        "xgb_model_ready": service.xgb_model is not None,
        "indexed_parcels": len(service.parcels_by_plot),
        "total_cases": len(service.cases),
        "db_type": service.db.db_type,
        "database_backend": service.db.db_type,
        "primary_database": "SQLITE",
        "neon_postgres": {
            "configured": service.db.neon_configured,
            "status": neon_status,
            "active_for_traffic": service.db.db_type == "POSTGRESQL",
        },
        "disclaimer": "SYNTHETIC DEMO — NOT AN OFFICIAL DOCUMENT. All records are synthetically generated.",
    }


@app.get("/api/dashboard/stats")
async def get_dashboard_statistics():
    """Returns comprehensive truthful statistics on datasets, models, and cases."""
    return service.get_dashboard_stats()


@app.get("/api/admin/dashboard-analytics")
async def get_admin_dashboard_analytics_endpoint(request: Request, year: Optional[str] = "2026"):
    """Returns interactive Bento-grid dashboard time-series and KPI analytics."""
    user = require_admin_access(request)
    return service.get_admin_dashboard_analytics(year=year)


@app.get("/api/samples")
async def list_sample_cases():
    """Returns the list of curated demo cases for instant one-click testing."""
    return service.get_sample_cases()


@app.get("/api/parcels/search")
async def search_parcels(q: str = "", limit: int = 20):
    """Searches cadastral parcels by plot number, mouza, parcel ID, upazila, or district."""
    return service.search_parcels(query=q, limit=limit)


@app.get("/api/parcels/{plot_or_id}")
async def get_parcel_detail(plot_or_id: str):
    """Returns parcel details, statutory survey chain of title, history, and mutations."""
    res = service.get_parcel_details(plot_or_id)
    if not res:
        raise HTTPException(status_code=404, detail=f"Parcel '{plot_or_id}' not found in cadastral registry.")
    return res


@app.get("/api/complaints")
async def api_list_complaints(request: Request, status: Optional[str] = None):
    """Returns citizen's complaints."""
    user = get_current_user(request)
    uid = user["user_id"] if user else None
    return service.list_complaints(user_id=uid, status=status)


@app.post("/api/complaints")
async def api_create_complaint(req: CreateComplaintRequest, request: Request):
    """Creates a new citizen grievance and links to investigation docket."""
    user = get_current_user(request)
    uid = user["user_id"] if user else "USR-CITIZEN-001"
    return service.create_complaint(uid, req.model_dump())


@app.get("/api/complaints/{complaint_id}")
async def api_get_complaint(complaint_id: str):
    """Retrieves single complaint details."""
    c = service.get_complaint(complaint_id)
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found.")
    return c


@app.post("/api/complaints/{complaint_id}/expedite")
async def api_request_expedite(complaint_id: str, req: ExpediteRequestPayload, request: Request):
    """Citizen requests expedited review on existing complaint."""
    user = get_current_user(request)
    uid = user["user_id"] if user else "USR-CITIZEN-001"
    c = service.request_expedited_review(complaint_id, user_id=uid, reason=req.reason)
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found.")
    return c


@app.post("/api/cases/{case_id}/expedite/decision")
async def api_decide_expedite(case_id: str, req: ExpediteDecisionPayload, request: Request):
    """Admin approves or rejects expedited review request."""
    user = get_current_user(request)
    officer_name = user["full_name"] if user else "Senior Registrar M. Rahman"
    c = service.decide_expedite(case_id, decision=req.decision, reason=req.reason, officer=officer_name)
    if not c:
        raise HTTPException(status_code=404, detail="Case or complaint not found.")
    return c


@app.get("/api/cases")
async def list_cases(status: Optional[str] = None, priority: Optional[str] = None):
    """Lists investigator review cases with optional status or priority filtering."""
    return service.list_cases(status=status, priority=priority)


@app.post("/api/cases")
async def create_case(req: CreateCaseRequest):
    """Creates a new investigator case."""
    return service.create_case(req.model_dump())


@app.get("/api/cases/{case_id}")
async def get_case(case_id: str):
    """Retrieves single case details."""
    c = service.get_case(case_id)
    if not c:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")
    return c


@app.patch("/api/cases/{case_id}")
async def update_case(case_id: str, req: UpdateCaseRequest):
    """Updates an existing investigation case."""
    c = service.update_case(case_id, req.model_dump(exclude_unset=True))
    if not c:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")
    return c


@app.post("/api/cases/{case_id}/notes")
async def add_case_note(case_id: str, req: AddCaseNoteRequest):
    """Appends an officer note to an investigation case."""
    c = service.add_case_note(case_id, note_text=req.note, author=req.author or "Officer")
    if not c:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")
    return c


@app.get("/api/reports/{verification_id}")
async def get_verification_report(verification_id: str):
    """Returns verification evidence report data with SHA-256 certificate hash."""
    rep = service.generate_report(verification_id)
    if not rep:
        raise HTTPException(status_code=404, detail=f"Verification '{verification_id}' not found.")
    return rep


@app.get("/api/reports/html/{verification_id}", response_class=HTMLResponse)
async def get_verification_report_html(verification_id: str):
    """Renders a printable official audit certificate and evidence dossier."""
    rep = service.generate_report(verification_id)
    if not rep:
        raise HTTPException(status_code=404, detail=f"Verification '{verification_id}' not found.")
    return templates.TemplateResponse(
        name="admin/report_detail.html",
        context={"report": rep},
        request=Request({"type": "http", "method": "GET", "path": "/"}),
    )


@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Accepts synthetic deed document (.png, .jpg, .jpeg, .pdf), validates size and format,
    runs bilingual OCR and CV checks, and returns extracted legal fields with uncertainty badges.
    """
    filename = file.filename or "unknown_document.png"
    contents = await file.read()

    try:
        result = service.process_document_upload(contents, filename)
        return JSONResponse(status_code=200, content=result)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document processing failed: {str(e)}")


@app.post("/api/verify")
async def verify_record(req: VerifyRequest):
    """
    Evaluates confirmed legal fields against Cadastral Registry,
    runs deterministic statutory rules, XGBoost inference, and CV anomaly checks.
    """
    try:
        result = service.verify_transaction(
            confirmed_fields=req.confirmed_fields,
            image_path=req.image_path,
            original_ocr_fields=req.original_ocr_fields,
        )
        return JSONResponse(status_code=200, content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")


@app.get("/api/history")
async def get_audit_history():
    """Returns recent verification audit logs."""
    return service.get_audit_history()


@app.post("/api/history/clear")
async def clear_audit_history():
    """Clears recent verification audit logs."""
    service.clear_audit_history()
    return {"message": "Audit history cleared."}


@app.get("/api/audit/trail")
async def get_audit_trail(limit: int = 50):
    """Returns immutable security and operational audit trail."""
    return service.get_audit_trail(limit=limit)


@app.get("/api/notifications")
async def get_notifications(request: Request):
    """Returns notifications for active user."""
    user = get_current_user(request)
    uid = user["user_id"] if user else "USR-CITIZEN-001"
    return service.get_notifications(uid)


@app.get("/api/image/{filename}")
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
