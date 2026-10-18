"""LandGuard Web Dependencies
Session resolution, authentication guards, and role-based access control (RBAC) dependencies.
"""

import os
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException, status
from fastapi.templating import Jinja2Templates

from src.landguard_web.service import service

templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)

import jinja2
from src.landguard_web.localization import get_text, get_preferred_language

@jinja2.pass_context
def _jinja_translate(context, key, **kwargs):
    request = context.get("request")
    lang = getattr(getattr(request, "state", None), "lang", None) or context.get("current_lang")
    if not lang and request:
        lang = get_preferred_language(request, context.get("current_user"))
    return get_text(key, lang=lang or "bn", **kwargs)

templates.env.globals["_"] = _jinja_translate
templates.env.globals["t"] = _jinja_translate
templates.env.filters["_"] = _jinja_translate
templates.env.filters["t"] = _jinja_translate

_orig_template_response = templates.TemplateResponse

def _wrapped_template_response(*args, **kwargs):
    context = kwargs.get("context")
    request = kwargs.get("request")
    if context is None and len(args) > 1 and isinstance(args[1], dict):
        context = args[1]
    if context is None and len(args) > 2 and isinstance(args[2], dict):
        context = args[2]

    if context is not None:
        if "current_lang" not in context:
            req = request or context.get("request")
            lang = None
            if req:
                lang = getattr(getattr(req, "state", None), "lang", None)
                if not lang:
                    try:
                        lang = get_preferred_language(req, context.get("current_user"))
                    except Exception:
                        lang = "bn"
            context["current_lang"] = lang or "bn"

    return _orig_template_response(*args, **kwargs)

templates.TemplateResponse = _wrapped_template_response


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
            headers={"Location": f"/login?redirect={request.url.path}"},
        )
    return user


def require_citizen_access(request: Request) -> Dict[str, Any]:
    """Citizen portal guard: ensures authenticated user is citizen or admin."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": f"/login?redirect={request.url.path}"},
        )
    return user


def require_admin_access(request: Request) -> Dict[str, Any]:
    """Admin / Investigator portal guard: denies CITIZEN role with 403 / access-denied."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": f"/login?redirect={request.url.path}"},
        )
    if user.get("role") == "CITIZEN":
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/access-denied"},
        )
    return user


def require_api_authenticated_user(request: Request) -> Dict[str, Any]:
    """Ensures caller has a valid active session or returns 401 Unauthorized for REST APIs."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in or provide a valid session token.",
        )
    return user


def require_api_admin_access(request: Request) -> Dict[str, Any]:
    """Ensures caller has ADMIN or INVESTIGATOR privileges or returns 403 Forbidden for REST APIs."""
    user = require_api_authenticated_user(request)
    if user.get("role") not in ["ADMIN", "INVESTIGATOR"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Administrative or investigator privileges required.",
        )
    return user
