"""Citizen Portal Router
Handles citizen dashboard, profile, preferences, notifications, and verification history.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from src.landguard_web.service import service
from src.landguard_web.dependencies import (
    templates,
    require_citizen_access,
)

router = APIRouter()


@router.get("/user/dashboard", response_class=HTMLResponse)
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


@router.get("/user/history", response_class=HTMLResponse)
async def citizen_history(request: Request):
    """Citizen's past verification submissions with status badges and report downloads."""
    user = require_citizen_access(request)
    history = service.get_audit_history(user_id=user["user_id"])
    return templates.TemplateResponse(
        request=request,
        name="user/history.html",
        context={
            "current_user": user,
            "history": history,
            "active_page": "history",
        },
    )


@router.get("/user/notifications", response_class=HTMLResponse)
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


@router.get("/user/profile", response_class=HTMLResponse)
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


@router.get("/user/settings", response_class=HTMLResponse)
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


@router.post("/api/user/preferences")
async def api_save_preferences(request: Request):
    """Saves user display/language preferences to SQLite and sets landguard_lang cookie."""
    from fastapi.responses import JSONResponse
    from src.landguard_web.dependencies import get_current_user

    data = {}
    try:
        data = await request.json()
    except Exception:
        pass
    pref_lang = data.get("preferred_language") or data.get("lang") or "bn"
    if pref_lang not in ["en", "bn"]:
        pref_lang = "bn"

    user = get_current_user(request)
    if user:
        service.update_user_preference(user["user_id"], preferred_language=pref_lang)

    res = JSONResponse({
        "status": "success",
        "preferred_language": pref_lang,
        "message": "Preferences updated successfully",
    })
    res.set_cookie(
        key="landguard_lang",
        value=pref_lang,
        max_age=31536000,
        samesite="lax",
        path="/",
    )
    return res
