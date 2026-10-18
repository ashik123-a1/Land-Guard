"""LandGuard Web Routers
Modular FastAPI route collections organized by domain responsibility.
"""

from src.landguard_web.routers.auth import router as auth_router
from src.landguard_web.routers.citizen import router as citizen_router
from src.landguard_web.routers.complaints import router as complaints_router
from src.landguard_web.routers.cases import router as cases_router
from src.landguard_web.routers.verifications import router as verifications_router
from src.landguard_web.routers.parcels import router as parcels_router
from src.landguard_web.routers.reports import router as reports_router
from src.landguard_web.routers.documents import router as documents_router
from src.landguard_web.routers.voice import router as voice_router
from src.landguard_web.routers.analytics import router as analytics_router

__all__ = [
    "auth_router",
    "citizen_router",
    "complaints_router",
    "cases_router",
    "verifications_router",
    "parcels_router",
    "reports_router",
    "documents_router",
    "voice_router",
    "analytics_router",
]
