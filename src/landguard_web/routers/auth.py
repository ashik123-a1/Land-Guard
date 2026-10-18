"""Authentication & Public Router
Manages landing, login/logout screens, demo authentication, and session inspection.
"""

import os
from typing import Optional
from fastapi import APIRouter, Request, Response, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from src.landguard_web.service import service
from src.landguard_web.schemas import LoginRequest
from src.landguard_web.dependencies import (
    templates,
    get_current_user,
)
from src.landguard_web.rate_limiter import enforce_rate_limit

router = APIRouter()


@router.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def landing_page(request: Request):
    """Public Landing / Welcome Page."""
    user = get_current_user(request)
    return templates.TemplateResponse(
        request=request,
        name="public/landing.html",
        context={
            "current_user": user,
            "banner_text": "SYNTHETIC DEMO — NOT AN OFFICIAL DOCUMENT",
        },
    )


def sanitize_redirect_path(url: Optional[str], default_path: str = "/user/dashboard") -> str:
    """Sanitizes redirect destination ensuring it is strictly a safe internal relative path.
    Rejects protocol-relative URLs (//evil.com), backslash variants (/\\evil.com), and external schemes.
    """
    if not url:
        return default_path
    clean = str(url).strip()
    if not clean:
        return default_path

    if clean.startswith("/") and not clean.startswith("//") and not clean.startswith("/\\"):
        from urllib.parse import urlparse
        try:
            parsed = urlparse(clean)
            if not parsed.scheme and not parsed.netloc:
                return clean
        except Exception:
            pass
    return default_path


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, redirect: Optional[str] = None):
    """Login Screen with credentials form and one-click demo role options."""
    user = get_current_user(request)
    default_dash = "/user/dashboard" if (user and user.get("role") == "CITIZEN") else "/admin/dashboard"
    safe_target = sanitize_redirect_path(redirect, default_dash)
    if user:
        return RedirectResponse(url=safe_target, status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        request=request,
        name="public/login.html",
        context={"redirect_target": sanitize_redirect_path(redirect, "")},
    )


@router.get("/access-denied", response_class=HTMLResponse)
async def access_denied_page(request: Request):
    """Displays 403 Forbidden Access Denied screen when a citizen attempts an admin route."""
    user = get_current_user(request)
    return templates.TemplateResponse(
        request=request,
        name="public/access_denied.html",
        context={"current_user": user},
    )


@router.get("/not-found", response_class=HTMLResponse)
async def not_found_page(request: Request):
    """Displays 404 page."""
    return templates.TemplateResponse(
        request=request,
        name="public/not_found.html",
        context={},
    )


@router.get("/logout")
async def logout(request: Request):
    """Terminates session, clears cookie, and redirects to /login."""
    session_id = request.cookies.get("landguard_session")
    if session_id:
        service.destroy_session(session_id)
    resp = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    resp.delete_cookie("landguard_session")
    return resp


@router.post("/api/auth/login")
async def api_login(req: LoginRequest, request: Request, response: Response):
    """Authenticates email and password, creates session, and sets cookie."""
    enforce_rate_limit(request, scope="auth_login", max_requests=10, window_seconds=60)
    user = service.authenticate_user(req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    session_id = service.create_session(user)
    default_dash = "/user/dashboard" if user.get("role") == "CITIZEN" else "/admin/dashboard"
    target = sanitize_redirect_path(req.redirect, default_dash)

    res = JSONResponse(content={"success": True, "redirect_url": target, "user": user})
    is_secure = os.getenv("ENVIRONMENT", "").lower() == "production"
    res.set_cookie(
        key="landguard_session",
        value=session_id,
        httponly=True,
        samesite="lax",
        secure=is_secure,
        max_age=86400 * 7,
    )
    return res


@router.post("/api/auth/demo-login")
async def api_demo_login(request: Request, role: str = "citizen"):
    """One-click demonstration role entry for testing (disabled in strict production)."""
    enforce_rate_limit(request, scope="auth_demo_login", max_requests=20, window_seconds=60)
    if os.getenv("ENVIRONMENT", "").lower() == "production" and os.getenv("ALLOW_DEMO_LOGIN_IN_PROD", "").lower() != "true":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="One-click demo login is disabled in production mode. Please use official authenticated credentials.",
        )

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
    is_secure = os.getenv("ENVIRONMENT", "").lower() == "production"
    res.set_cookie(
        key="landguard_session",
        value=session_id,
        httponly=True,
        samesite="lax",
        secure=is_secure,
        max_age=86400 * 7,
    )
    return res


@router.post("/api/auth/logout")
async def api_logout(request: Request):
    """Terminates session on logout."""
    session_id = request.cookies.get("landguard_session")
    if session_id:
        service.destroy_session(session_id)
    res = JSONResponse(content={"success": True, "message": "Logged out."})
    res.delete_cookie("landguard_session")
    return res


@router.get("/api/auth/me")
async def api_auth_me(request: Request):
    """Returns currently authenticated user profile."""
    user = get_current_user(request)
    if not user:
        return {"authenticated": False, "user": None}
    return {"authenticated": True, "user": user}
