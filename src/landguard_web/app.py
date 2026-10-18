"""LandGuard FastAPI Web Application
Provides interactive browser UI, login-first authentication, separate Citizen and Admin portals,
document upload, bilingual OCR extraction, cadastral registry verification, ML & CV supplementary evidence,
docket case management, and immutable audit logs.

Refactored into a clean, modular architecture:
- Presentation & Routes: src/landguard_web/routers/
- Domain Services: src/landguard_services/
- Data Repositories: src/landguard_data/repositories/
"""

import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.landguard_web.service import service, LandGuardVerificationService
from src.landguard_web.dependencies import (
    templates,
    get_current_user,
    require_authenticated_user,
    require_citizen_access,
    require_admin_access,
    require_api_authenticated_user,
    require_api_admin_access,
)
from src.landguard_web.schemas import (
    LoginRequest,
    VerifyRequest,
    CreateCaseRequest,
    UpdateCaseRequest,
    AddCaseNoteRequest,
    CreateComplaintRequest,
    ExpediteRequestPayload,
    ExpediteDecisionPayload,
    VerificationDecisionRequest,
    UpdateReportStatusRequest,
    VoiceIntentRequest,
    CaseClarificationRequest,
    CaseClarificationResponse,
    WhatIfSimulationRequest,
)
from src.landguard_web.routers import (
    auth_router,
    citizen_router,
    complaints_router,
    cases_router,
    verifications_router,
    parcels_router,
    reports_router,
    documents_router,
    voice_router,
    analytics_router,
)

app = FastAPI(
    title="LandGuard AI Land Record Verification",
    description="Statutory land deed verification, bilingual OCR, and multi-modal risk assessment.",
    version="2.0.0",
)

# CORS configuration for cross-origin / reverse-proxy deployments
from fastapi.middleware.cors import CORSMiddleware

allowed_origins_env = os.environ.get("ALLOWED_ORIGINS", "")
if allowed_origins_env.strip():
    allowed_origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Mount static asset directory
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

from fastapi.responses import FileResponse

@app.get("/favicon.ico", include_in_schema=False)
async def get_favicon():
    ico_path = os.path.join(os.path.dirname(__file__), "static", "images", "favicon.ico")
    if os.path.exists(ico_path):
        return FileResponse(ico_path, media_type="image/x-icon")
    svg_path = os.path.join(os.path.dirname(__file__), "static", "images", "favicon.svg")
    return FileResponse(svg_path, media_type="image/svg+xml")


@app.api_route("/health", methods=["GET", "HEAD"])
@app.api_route("/api/health", methods=["GET", "HEAD"])
async def health_check():
    return {"status": "healthy", "service": "landguard"}


from fastapi import Request
from src.landguard_web.localization import get_preferred_language

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "microphone=(self)"
    return response


@app.middleware("http")
async def language_middleware(request: Request, call_next):
    user = get_current_user(request)
    lang = get_preferred_language(request=request, user=user)
    request.state.lang = lang
    response = await call_next(request)
    try:
        q_lang = request.query_params.get("lang")
        if q_lang in ["en", "bn"]:
            response.set_cookie(
                key="landguard_lang",
                value=q_lang,
                max_age=31536000,
                samesite="lax",
                path="/",
            )
    except Exception:
        pass
    return response

# ---------------------------------------------------------
# Mount Modular Domain Routers
# ---------------------------------------------------------

app.include_router(auth_router)
app.include_router(citizen_router)
app.include_router(complaints_router)
app.include_router(cases_router)
app.include_router(verifications_router)
app.include_router(parcels_router)
app.include_router(reports_router)
app.include_router(documents_router)
app.include_router(voice_router)
app.include_router(analytics_router)

# Export compatibility symbols for existing tests and external scripts
__all__ = [
    "app",
    "service",
    "templates",
    "LandGuardVerificationService",
    "get_current_user",
    "require_authenticated_user",
    "require_citizen_access",
    "require_admin_access",
    "require_api_authenticated_user",
    "require_api_admin_access",
    "LoginRequest",
    "VerifyRequest",
    "CreateCaseRequest",
    "UpdateCaseRequest",
    "AddCaseNoteRequest",
    "CreateComplaintRequest",
    "ExpediteRequestPayload",
    "ExpediteDecisionPayload",
    "VerificationDecisionRequest",
    "UpdateReportStatusRequest",
    "VoiceIntentRequest",
    "CaseClarificationRequest",
    "CaseClarificationResponse",
    "WhatIfSimulationRequest",
]

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run("src.landguard_web.app:app", host=host, port=port, reload=False)

