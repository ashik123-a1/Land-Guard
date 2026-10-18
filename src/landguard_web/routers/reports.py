"""LandGuard Reports Router
Evidence dossier certificates, printable HTML, binary PDF generation, dynamic QR codes,
public sanitized verification, and report lifecycle management.
"""

from typing import Optional
from fastapi import APIRouter, Request, Response, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse

from src.landguard_web.service import service
from src.landguard_web.dependencies import (
    templates,
    get_current_user,
    require_admin_access,
    require_api_admin_access,
)
from src.landguard_web.schemas import UpdateReportStatusRequest
from src.landguard_web.localization import get_preferred_language

router = APIRouter(tags=["reports"])


# ---------------------------------------------------------
# Human-Readable Report HTML Views
# ---------------------------------------------------------

@router.get("/reports/{verification_id}", response_class=HTMLResponse)
async def view_formatted_report(request: Request, verification_id: str):
    """Human-readable formatted HTML report view.
    Renders administrative evidence report for staff, and sanitized public certificate for citizens/guests.
    """
    try:
        user = get_current_user(request)
        pref_lang = get_preferred_language(request, user)
        is_staff = user and user.get("role") in ["ADMIN", "INVESTIGATOR"]
        if is_staff:
            rep = service.generate_report(verification_id)
            if not rep:
                return RedirectResponse(url="/not-found", status_code=status.HTTP_303_SEE_OTHER)
            return templates.TemplateResponse(
                request=request,
                name="admin/report_detail.html",
                context={
                    "request": request,
                    "report": rep,
                    "current_user": user,
                    "current_lang": pref_lang,
                },
            )

        sanitized = service.get_sanitized_public_verification(verification_id)
        if not sanitized:
            return RedirectResponse(url="/not-found", status_code=status.HTTP_303_SEE_OTHER)

        return templates.TemplateResponse(
            request=request,
            name="public/verification_certificate.html",
            context={
                "request": request,
                "record": sanitized,
                "current_user": user,
                "current_lang": pref_lang,
            },
        )
    except Exception as e:
        import traceback
        print(f"[REPORTS ERROR] {traceback.format_exc()}", flush=True)
        return HTMLResponse(
            content="""<!DOCTYPE html><html><head><title>Report Error</title></head>
            <body style='font-family: sans-serif; text-align: center; padding: 50px; background: #0f172a; color: #f8fafc;'>
                <h2 style='color: #f43f5e;'>Unable to Load Statutory Verification Dossier</h2>
                <p style='color: #94a3b8;'>An internal error occurred while generating this certificate view.</p>
                <a href='/' style='color: #38bdf8;'>Return to Home</a>
            </body></html>""",
            status_code=500,
        )


@router.get("/reports/{verification_id}/print", response_class=HTMLResponse)
@router.get("/verify/print/{verification_id}", response_class=HTMLResponse)
async def print_verification_report(request: Request, verification_id: str):
    """Renders printable official audit certificate and evidence dossier.
    Authorized staff and record owners receive the unmasked administrative dossier;
    public visitors receive the privacy-sanitized public certificate.
    """
    user = get_current_user(request)
    pref_lang = get_preferred_language(request, user)
    rec = service.get_verification_record(verification_id)
    if not rec:
        return RedirectResponse(url="/not-found", status_code=status.HTTP_303_SEE_OTHER)

    is_staff = user and user.get("role") in ["ADMIN", "INVESTIGATOR"]
    is_owner = user and (rec.get("user_id") == user.get("user_id"))

    if is_staff or is_owner:
        rep = service.generate_report(verification_id)
        return templates.TemplateResponse(
            request=request,
            name="admin/report_detail.html",
            context={"request": request, "report": rep, "current_user": user, "current_lang": pref_lang},
        )

    # Public printable view: sanitized public certificate with masked PII
    sanitized = service.get_sanitized_public_verification(verification_id)
    return templates.TemplateResponse(
        request=request,
        name="public/verification_certificate.html",
        context={"request": request, "record": sanitized, "current_user": user, "current_lang": pref_lang, "is_print": True},
    )


# ---------------------------------------------------------
# Admin Report HTML Views
# ---------------------------------------------------------

@router.get("/admin/reports", response_class=HTMLResponse)
async def admin_reports(request: Request):
    """Evidence dossiers list with SHA-256 certificate hashes."""
    user = require_admin_access(request)
    pref_lang = get_preferred_language(request, user)
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
            "request": request,
            "current_user": user,
            "reports": generated_reports,
            "active_page": "reports",
            "current_lang": pref_lang,
        },
    )


@router.get("/admin/reports/{verification_id}", response_class=HTMLResponse)
async def admin_report_detail(request: Request, verification_id: str):
    """Official printable Evidence Dossier Certificate."""
    user = require_admin_access(request)
    pref_lang = get_preferred_language(request, user)
    rep = service.generate_report(verification_id)
    if not rep:
        return RedirectResponse(url="/not-found", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        request=request,
        name="admin/report_detail.html",
        context={"request": request, "report": rep, "current_user": user, "current_lang": pref_lang},
    )


# ---------------------------------------------------------
# Report API Endpoints
# ---------------------------------------------------------

@router.get("/api/reports/{verification_id}")
async def get_verification_report(verification_id: str, request: Request):
    """Returns verification evidence report data with SHA-256 certificate hash.
    Authorized staff and record owners receive the full statutory dossier.
    Public and unauthenticated callers receive the privacy-sanitized verification record.
    """
    user = get_current_user(request)
    rec = service.get_verification_record(verification_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Verification '{verification_id}' not found.")

    is_staff = user and user.get("role") in ["ADMIN", "INVESTIGATOR"]
    is_owner = user and (rec.get("user_id") == user.get("user_id"))

    if is_staff or is_owner:
        rep = service.generate_report(verification_id)
        return rep

    # Public privacy-preserving response (masked citizen PII)
    sanitized = service.get_sanitized_public_verification(verification_id)
    return {
        "report_id": f"REP-PUB-{verification_id}",
        "verification": sanitized,
        "sha256_certificate_hash": sanitized.get("sha256_hash"),
        "is_public_sanitized": True,
        "legal_notice": "Public verification view (sensitive citizen PII masked under LandGuard statutory data protection policy).",
    }


@router.get("/api/reports/html/{verification_id}", response_class=HTMLResponse)
@router.get("/reports/{verification_id}/html", response_class=HTMLResponse)
async def get_verification_report_html(verification_id: str, request: Request, lang: Optional[str] = None):
    """Renders a printable official audit certificate and evidence dossier.
    Restricted to authorized staff and owning citizen; public requests receive the sanitized certificate.
    """
    user = get_current_user(request)
    pref_lang = lang or get_preferred_language(request, user)
    rec = service.get_verification_record(verification_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Verification '{verification_id}' not found.")

    is_staff = user and user.get("role") in ["ADMIN", "INVESTIGATOR"]
    is_owner = user and (rec.get("user_id") == user.get("user_id"))

    if is_staff or is_owner:
        rep = service.generate_report(verification_id)
        return templates.TemplateResponse(
            name="admin/report_detail.html",
            context={"request": request, "report": rep, "current_lang": pref_lang, "current_user": user},
            request=request,
        )

    # Public callers receive the sanitized certificate view
    sanitized = service.get_sanitized_public_verification(verification_id)
    return templates.TemplateResponse(
        name="public/verification_certificate.html",
        context={"request": request, "record": sanitized, "current_lang": pref_lang, "current_user": user},
        request=request,
    )


@router.get("/api/reports/pdf/{verification_id}")
@router.get("/reports/{verification_id}/pdf")
async def get_verification_report_pdf(
    verification_id: str,
    request: Request,
    lang: Optional[str] = None,
):
    """Generates and returns an authoritative binary PDF verification dossier."""
    user = get_current_user(request)
    pref_lang = lang or get_preferred_language(request, user)
    base_url = str(request.base_url).rstrip("/")
    pdf_bytes = service.generate_pdf_report(verification_id, base_url=base_url, lang=pref_lang)
    if not pdf_bytes:
        raise HTTPException(status_code=404, detail=f"Verification '{verification_id}' not found.")
    filename = (
        f"LandGuard_Dossier_{verification_id}_bn.pdf"
        if lang == "bn"
        else f"LandGuard_Dossier_{verification_id}.pdf"
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"'
        },
    )


@router.get("/api/reports/qr/{verification_id}")
@router.get("/reports/{verification_id}/qr")
async def get_verification_report_qr(verification_id: str, request: Request):
    """Returns dynamic QR code image (PNG) linking to public verification portal."""
    from src.landguard_reports.qr_generator import generate_verification_qr
    base_url = str(request.base_url).rstrip("/")
    qr_png = generate_verification_qr(verification_id, base_url=base_url)
    return Response(content=qr_png, media_type="image/png")


@router.get("/api/reports/public/{verification_id}")
@router.get("/api/verify/public/{verification_id}")
async def get_public_verification_json(verification_id: str):
    """Returns sanitized verification status with citizen PII masked for public verification."""
    sanitized = service.get_sanitized_public_verification(verification_id)
    if not sanitized:
        raise HTTPException(status_code=404, detail=f"Verification '{verification_id}' not found.")
    return sanitized


@router.get("/verify/public/{verification_id}", response_class=HTMLResponse)
async def public_verification_page(verification_id: str, request: Request):
    """Renders public-facing certificate page with masked citizen PII and live lifecycle status."""
    user = get_current_user(request)
    pref_lang = get_preferred_language(request, user)
    sanitized = service.get_sanitized_public_verification(verification_id)
    if not sanitized:
        return RedirectResponse(url="/not-found", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        name="public/verification_certificate.html",
        context={"request": request, "record": sanitized, "current_user": user, "current_lang": pref_lang},
        request=request,
    )


@router.patch("/api/reports/{verification_id}/status")
async def update_report_status_endpoint(
    verification_id: str,
    req: UpdateReportStatusRequest,
    request: Request,
):
    """Updates verification report lifecycle status (VALID, WITHDRAWN, SUPERSEDED, RE_REVIEW_REQUIRED). Requires Admin/Investigator."""
    user = require_api_admin_access(request)
    try:
        updated = service.update_report_status(
            verification_id=verification_id,
            new_status=req.status,
            reason=req.reason,
            user_id=user["user_id"],
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Verification dossier '{verification_id}' not found.")

    return {
        "success": True,
        "verification_id": verification_id,
        "report_status": updated.get("report_status"),
        "status_reason": updated.get("status_reason"),
        "updated_at": updated.get("updated_at"),
        "message": f"Report lifecycle status updated to '{req.status.upper()}'.",
    }
