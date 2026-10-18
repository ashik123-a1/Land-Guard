"""LandGuard Parcels Router
Cadastral parcel search, survey chains (CS/SA/RS/BS), topology graph, and what-if simulation.
"""

from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

from src.landguard_web.service import service
from src.landguard_web.dependencies import (
    templates,
    get_current_user,
    require_citizen_access,
    require_admin_access,
)
from src.landguard_web.schemas import WhatIfSimulationRequest

router = APIRouter(tags=["parcels"])


# ---------------------------------------------------------
# Citizen Parcel HTML Views
# ---------------------------------------------------------

@router.get("/user/parcels", response_class=HTMLResponse)
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


@router.get("/user/parcels/{plot_or_id}", response_class=HTMLResponse)
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


# ---------------------------------------------------------
# Admin Parcel HTML Views
# ---------------------------------------------------------

@router.get("/admin/parcels", response_class=HTMLResponse)
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


# ---------------------------------------------------------
# Parcel API Endpoints
# ---------------------------------------------------------

@router.get("/api/parcels/search")
async def search_parcels(q: str = "", limit: int = 20):
    """Searches cadastral parcels by plot number, mouza, parcel ID, upazila, or district."""
    return service.search_parcels(query=q, limit=limit)


@router.get("/api/parcels/{plot_or_id}")
async def get_parcel_detail(plot_or_id: str):
    """Retrieves full cadastral profile, mutation chain, and deed history for a parcel."""
    res = service.get_parcel_details(plot_or_id)
    if not res:
        raise HTTPException(status_code=404, detail=f"Cadastral parcel '{plot_or_id}' not found.")
    return res


@router.get("/api/parcels/{plot_or_id}/graph")
@router.get("/api/parcels/{plot_or_id}/cadastral-graph")
async def get_parcel_cadastral_graph_endpoint(plot_or_id: str):
    """Returns nodes and edges representing cadastral parcel ownership and sub-plots."""
    graph = service.get_cadastral_graph(plot_or_id)
    if not graph:
        raise HTTPException(status_code=404, detail=f"Cadastral parcel '{plot_or_id}' not found.")
    return graph


@router.post("/api/simulator/what-if")
@router.post("/api/parcels/what-if")
async def simulate_what_if_endpoint(req: WhatIfSimulationRequest):
    """
    Simulates hypothetical transaction without writing to operational database.
    Evaluates parcel capacity, seller legitimacy, double-selling risk, and projected state.
    """
    return JSONResponse(status_code=200, content=service.simulate_what_if_transaction(req.model_dump()))


@router.get("/api/parcels/{plot_or_id}/cross-parcel-patterns")
@router.get("/api/parcels/{plot_or_id}/patterns")
async def get_cross_parcel_patterns_endpoint(plot_or_id: str):
    """
    Analyzes multi-parcel conveyance patterns for an entity or parcel across the cadastral registry.
    Discloses evidence-linked relationships without labeling coincidental matches as proven fraud.
    """
    patterns = service.analyze_cross_parcel_patterns(plot_or_id)
    return JSONResponse(status_code=200, content=patterns)


@router.post("/admin/parcels/create")
@router.post("/api/parcels/create")
async def create_parcel_endpoint(request: Request):
    """
    Creates and registers a new cadastral land parcel.
    Enforces strict duplicate rejection: if the dag plot number already exists in that mouza,
    it returns HTTP 409 Conflict with an explicit error message.
    """
    user = get_current_user(request)
    if not user:
        accept = request.headers.get("accept", "")
        content_type = request.headers.get("content-type", "")
        if "application/json" in accept or "application/json" in content_type:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": f"/login?redirect={request.url.path}"},
        )

    if user.get("role") == "CITIZEN":
        accept = request.headers.get("accept", "")
        content_type = request.headers.get("content-type", "")
        if "application/json" in accept or "application/json" in content_type:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or Land Officer access required.")
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/access-denied"},
        )

    # Parse JSON or form data
    try:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            payload = await request.json()
        else:
            form = await request.form()
            payload = dict(form)
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "conflict": False, "error": f"Invalid payload: {str(e)}"},
        )

    actor_id = user.get("user_id", "USR-ADMIN-001") if isinstance(user, dict) else getattr(user, "user_id", "USR-ADMIN-001")
    result = service.create_parcel(payload, actor_id=actor_id)

    if result.get("conflict"):
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=result)
    elif not result.get("success"):
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=result)

    return JSONResponse(status_code=status.HTTP_201_CREATED, content=result)


