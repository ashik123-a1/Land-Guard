"""LandGuard Analytics & Administration Router
Admin dashboard, Bento-grid metrics, health check, audit trails, and system governance.
"""

from typing import Optional
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from src.landguard_web.service import service
from src.landguard_web.dependencies import (
    templates,
    get_current_user,
    require_admin_access,
)

router = APIRouter(tags=["analytics"])


# ---------------------------------------------------------
# Admin Portal HTML Views
# ---------------------------------------------------------

@router.get("/admin/dashboard", response_class=HTMLResponse)
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


@router.get("/admin/analytics", response_class=HTMLResponse)
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


@router.get("/admin/audit", response_class=HTMLResponse)
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


@router.get("/admin/users", response_class=HTMLResponse)
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


@router.get("/admin/models", response_class=HTMLResponse)
async def admin_models(request: Request):
    """AI Model Governance card."""
    user = require_admin_access(request)
    model_eval = service.get_model_evaluation_metrics()
    return templates.TemplateResponse(
        request=request,
        name="admin/models.html",
        context={
            "current_user": user,
            "model_eval": model_eval,
            "active_page": "models",
        },
    )


@router.get("/admin/system", response_class=HTMLResponse)
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


@router.get("/admin/settings", response_class=HTMLResponse)
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
# Operational API Endpoints
# ---------------------------------------------------------

@router.api_route("/health", methods=["GET", "HEAD"])
@router.api_route("/api/health", methods=["GET", "HEAD"])
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


@router.get("/api/dashboard/stats")
@router.get("/api/stats")
async def get_dashboard_statistics():
    """Returns comprehensive truthful statistics on datasets, models, and cases."""
    return service.get_dashboard_stats()


@router.get("/api/admin/dashboard-analytics")
@router.get("/api/admin/dashboard/analytics")
async def get_admin_dashboard_analytics_endpoint(request: Request, year: Optional[str] = "2026"):
    """Returns interactive Bento-grid dashboard time-series and KPI analytics."""
    require_admin_access(request)
    return service.get_admin_dashboard_analytics(year=year)


@router.get("/api/history")
async def get_audit_history():
    """Returns recent verification audit logs."""
    return service.get_audit_history()


@router.post("/api/history/clear")
async def clear_audit_history():
    """Clears recent verification audit logs."""
    service.clear_audit_history()
    return {"message": "Audit history cleared."}


@router.get("/api/audit/trail")
@router.get("/api/audit-trail")
async def get_audit_trail(limit: int = 50):
    """Returns immutable security and operational audit trail."""
    return service.get_audit_trail(limit=limit)


@router.get("/api/notifications")
async def get_notifications(request: Request):
    """Returns notifications for active user."""
    user = get_current_user(request)
    uid = user["user_id"] if user else "USR-CITIZEN-001"
    return service.get_notifications(uid)


@router.post("/api/notifications/{notification_id}/read")
async def mark_notification_read_endpoint(notification_id: str, request: Request):
    """Marks single notification as read."""
    user = get_current_user(request)
    uid = user["user_id"] if user else "USR-CITIZEN-001"
    success = service.mark_notification_read(notification_id, uid)
    return {"success": success, "notification_id": notification_id}


@router.post("/api/notifications/read-all")
async def mark_all_notifications_read_endpoint(request: Request):
    """Marks all notifications as read for current user."""
    user = get_current_user(request)
    uid = user["user_id"] if user else "USR-CITIZEN-001"
    count = service.mark_all_notifications_read(uid)
    return {"success": True, "count": count}


# ---------------------------------------------------------
# Rule Governance & Scenarios API
# ---------------------------------------------------------

@router.get("/api/admin/rules")
async def get_admin_rules(request: Request):
    """Returns active statutory ruleset and historical version ledger. Requires Admin/Investigator access."""
    require_admin_access(request)
    return {
        "active_ruleset": service.get_active_ruleset(),
        "version_history": service.get_ruleset_history(),
    }


@router.post("/api/admin/rules/update")
async def update_admin_rules(request: Request):
    """Updates statutory ruleset configuration with mandatory justification and immutable versioning."""
    user = require_admin_access(request)
    try:
        body = await request.json()
    except Exception:
        body = {}
    justification = body.get("justification", "")
    new_rules = body.get("rules")
    new_thresholds = body.get("thresholds")
    officer_name = user.get("full_name", "Senior Registrar M. Rahman")
    try:
        updated = service.update_ruleset(
            new_rules=new_rules,
            new_thresholds=new_thresholds,
            officer=officer_name,
            justification=justification,
        )
        return updated
    except ValueError as ve:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(ve))


@router.get("/api/scenarios/catalog")
async def get_scenario_catalog():
    """Lists all available reproducible synthetic scenario archetypes."""
    return service.get_scenario_catalog()


@router.post("/api/scenarios/generate")
async def generate_synthetic_scenario(request: Request):
    """Deterministically generates synthetic scenario with zero operational database writes."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    scenario_type = body.get("scenario_type", "CONFLICTING_DOUBLE_SALE")
    seed = body.get("seed", 42)
    try:
        return service.generate_reproducible_scenario(scenario_type=scenario_type, seed=seed)
    except ValueError as ve:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(ve))

