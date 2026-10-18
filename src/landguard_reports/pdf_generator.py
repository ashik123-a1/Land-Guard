"""LandGuard PDF Verification Dossier Generator.
Produces high-fidelity, tamper-evident PDF verification dossiers with embedded QR codes,
statutory rule findings, multivariate risk scores, cryptographic SHA-256 signatures,
and required synthetic demonstration disclaimers.

Supports:
1. Headless Chrome/Edge rendering with native HarfBuzz Indic glyph shaping for authentic Bengali (যুক্তাক্ষর).
2. ReportLab vector document rendering fallback with Windows Nirmala UI / TrueType font integration.
"""

import io
import os
import shutil
import base64
import tempfile
import subprocess
import datetime
from typing import Dict, Any, Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage,
    KeepTogether,
    HRFlowable,
)

from src.landguard_reports.qr_generator import generate_verification_qr, get_public_base_url
from src.landguard_web.localization import translate
from src.landguard_models.verification_rules import RULE_METADATA


def _find_browser_executable() -> Optional[str]:
    """Locates an available modern Chromium-based browser with native HarfBuzz Indic shaping."""
    candidates = [
        os.environ.get("CHROME_BIN"),
        os.environ.get("BROWSER_PATH"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        shutil.which("google-chrome"),
        shutil.which("chrome"),
        shutil.which("chromium"),
        shutil.which("msedge"),
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return None


def _build_dossier_html(
    verification_record: Dict[str, Any],
    base_url: Optional[str] = None,
    lang: str = "bn",
) -> str:
    """Builds a complete, standalone, print-ready HTML dossier with authentic typography and embedded assets."""
    target_lang = lang if lang in ["en", "bn"] else "bn"
    _ = lambda k: translate(k, target_lang)

    v_id = verification_record.get("verification_id", "VRF-UNKNOWN")
    issued_at = verification_record.get("timestamp") or datetime.datetime.now().isoformat()
    overall_status = verification_record.get("overall_status", "PENDING")
    report_status = (verification_record.get("report_status") or "VALID").upper()
    status_reason = verification_record.get("status_reason", "")

    parcel = verification_record.get("cadastral_parcel") or {}
    mouza = parcel.get("mouza") or verification_record.get("mouza") or "N/A"
    upazila = parcel.get("upazila") or verification_record.get("upazila") or "N/A"
    district = parcel.get("district") or verification_record.get("district") or "N/A"

    def mask_val(val: Optional[str]) -> str:
        if not val:
            return "N/A"
        s = str(val).strip()
        if len(s) <= 4:
            return "****"
        if s.isdigit() and len(s) >= 10:
            return f"{s[:6]}{'*' * (len(s) - 10)}{s[-4:]}"
        if "-" in s:
            p = s.split("-")
            return f"{p[0]}-***-{p[-1][-4:]}"
        return f"{s[:3]}***{s[-3:]}" if len(s) > 6 else "****"

    seller_nid = verification_record.get("seller_nid") or "N/A"
    buyer_nid = verification_record.get("buyer_nid") or "N/A"
    masked_seller = mask_val(seller_nid)
    masked_buyer = mask_val(buyer_nid)

    sha256_hash = verification_record.get("sha256_hash") or verification_record.get("sha256_certificate_hash", "UNCOMPUTED")
    clean_base = get_public_base_url(base_url)

    # Dynamic QR code
    qr_bytes = generate_verification_qr(v_id, base_url=clean_base, box_size=4, border=1)
    qr_b64 = base64.b64encode(qr_bytes).decode("ascii")

    # Status theme styling
    if report_status == "WITHDRAWN":
        status_theme = "border: 2px solid #ef4444; background: #fef2f2; color: #991b1b;"
        status_title = _("CERTIFICATE FORMALLY WITHDRAWN & REVOKED")
        status_sub = f"{_('This verification certificate was revoked by registrar administrative order on')} {issued_at[:10]}."
    elif report_status == "SUPERSEDED":
        status_theme = "border: 2px solid #f59e0b; background: #fffbeb; color: #92400e;"
        status_title = _("CERTIFICATE SUPERSEDED BY REVISED DETERMINATION")
        status_sub = _("A subsequent administrative review has superseded this preliminary record.")
    elif overall_status == "CLEAR_FOR_STANDARD_PROCESSING":
        status_theme = "border: 2px solid #10b981; background: #ecfdf5; color: #065f46;"
        status_title = _("CLEAR FOR STANDARD PROCESSING")
        status_sub = _("All statutory title chain and capacity checks verified without contradiction.")
    elif overall_status == "MISSING_EVIDENCE":
        status_theme = "border: 2px solid #f59e0b; background: #fffbeb; color: #92400e;"
        status_title = _("MISSING EVIDENCE / UNINDEXED ARCHIVE")
        status_sub = _("Requires physical sub-registry volume lookup. Not flagged as fraudulent.")
    else:
        status_theme = "border: 2px solid #ef4444; background: #fef2f2; color: #991b1b;"
        status_title = _("CONFIRMED STATUTORY CONTRADICTION")
        status_sub = _("Deterministic statutory violation or conflicting double disposition detected.")

    ml_score = verification_record.get("ml_risk_score", 0.0)
    ml_pct = f"{float(ml_score)*100:.2f}%" if ml_score is not None else "N/A"
    ml_eval = _("High-Risk Deeds") if (ml_score is not None and float(ml_score) > 0.35) else _("Clear Titles")

    cv_ev = verification_record.get("cv_evidence") or {}
    cv_anom = cv_ev.get("visual_anomaly_score", 0.0)
    cv_pct = f"{float(cv_anom)*100:.1f}%" if cv_anom is not None else "N/A"
    seal_status = _("DETECTED") if (cv_ev.get("seal_present") or cv_ev.get("seal_status") == "DETECTED") else _("MISSING / UNCERTAIN")
    sig_status = _("PRESENT") if (cv_ev.get("signature_present") or cv_ev.get("signature_status") == "DETECTED") else _("MISSING / UNCERTAIN")

    rules = verification_record.get("rules_triggered", [])

    rules_html = ""
    if not rules:
        rules_html = f"""
        <div style="background: #ecfdf5; border: 1px solid #10b981; border-radius: 6px; padding: 10px 14px; font-size: 10.5px; color: #065f46;">
            <strong>{_('Clean Statutory Audit:')}</strong> {_('No configured statutory contradictions triggered during algorithmic evaluation against registered cadastral ledgers.')}
        </div>
        """
    else:
        rows = []
        for r in rules:
            code = r.get("rule_code", "STATUTORY_RULE")
            meta = RULE_METADATA.get(code, {})
            title = r.get("title_bn") if (target_lang == "bn" and r.get("title_bn")) else (meta.get("title_bn") if target_lang == "bn" else _(r.get("title") or code))
            sev = _(r.get("severity", "HIGH"))
            if target_lang == "bn":
                expl = r.get("explanation_bn") or meta.get("default_explanation_bn") or _(r.get("explanation") or r.get("reason", ""))
            else:
                expl = _(r.get("explanation") or r.get("reason", ""))
            stat_ref = r.get("statutory_reference") or meta.get("statutory_reference") or "Registration Act 1908"
            sev_badge_bg = "#fee2e2" if "CRITICAL" in r.get("severity", "").upper() else ("#fef3c7" if "HIGH" in r.get("severity", "").upper() else "#e0f2fe")
            sev_badge_color = "#991b1b" if "CRITICAL" in r.get("severity", "").upper() else ("#92400e" if "HIGH" in r.get("severity", "").upper() else "#0369a1")

            rows.append(f"""
            <div style="border: 1px solid #fecaca; background: #fff5f5; border-radius: 6px; padding: 8px 12px; margin-bottom: 6px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 3px;">
                    <span style="font-weight: 700; font-size: 11px; color: #1e293b;">{title} ({code})</span>
                    <span style="background: {sev_badge_bg}; color: {sev_badge_color}; padding: 2px 6px; border-radius: 4px; font-size: 9.5px; font-weight: 700;">{sev}</span>
                </div>
                <div style="font-size: 10px; color: #334155; margin-bottom: 2px;">{expl}</div>
                <div style="font-size: 9px; color: #64748b; font-family: monospace;">{_('Authority:')} {stat_ref}</div>
            </div>
            """)
        rules_html = "".join(rows)

    human_det = verification_record.get("human_determination")
    human_det_html = ""
    if human_det:
        det_dec = _(human_det.get("decision", "REVIEW_RECORDED"))
        det_officer = human_det.get("officer_name", "Authorized Officer")
        det_ts = human_det.get("timestamp", "N/A")
        det_reason = human_det.get("reason", "")
        human_det_html = f"""
        <div style="margin-top: 14px; border: 1.5px solid #10b981; background: #f0fdf4; border-radius: 8px; padding: 10px 14px;">
            <div style="font-size: 11px; font-weight: 700; color: #166534; text-transform: uppercase; margin-bottom: 4px;">{_('Official Registrar Determination')}</div>
            <div style="font-size: 10.5px; color: #1e293b;"><strong>{det_dec}</strong> &bull; {det_officer} ({det_ts})</div>
            <div style="font-size: 10px; color: #475569; margin-top: 2px;"><em>{det_reason}</em></div>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="{target_lang}">
<head>
    <meta charset="utf-8">
    <title>{_('Official Verification Certificate')} — {v_id}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@700&family=Hind+Siliguri:wght@400;500;600;700&family=Noto+Sans+Bengali:wght@400;500;600;700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
        @page {{
            size: letter;
            margin: 10mm 14mm;
        }}
        body {{
            font-family: 'Hind Siliguri', 'Noto Sans Bengali', 'Inter', 'Nirmala UI', sans-serif;
            color: #0f172a;
            background: #ffffff;
            margin: 0;
            padding: 0;
            font-size: 10.5px;
            line-height: 1.45;
        }}
        .cert-container {{
            border: 3px double #0f172a;
            padding: 18px 22px;
            background: #ffffff;
            position: relative;
        }}
        .watermark {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%) rotate(-32deg);
            font-size: 42px;
            font-weight: 900;
            color: rgba(239, 68, 68, 0.05);
            pointer-events: none;
            white-space: nowrap;
            letter-spacing: 4px;
            text-transform: uppercase;
            font-family: 'Cinzel', serif;
        }}
        .header {{
            text-align: center;
            border-bottom: 2px solid #0f172a;
            padding-bottom: 10px;
            margin-bottom: 12px;
        }}
        .title {{
            font-size: 17px;
            font-weight: 800;
            margin: 3px 0;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .disclaimer-pill {{
            display: inline-block;
            background: #fff1f2;
            border: 1px solid #fecdd3;
            color: #be123c;
            font-size: 9.5px;
            font-weight: 700;
            padding: 2px 10px;
            border-radius: 4px;
            margin-top: 4px;
        }}
        .meta-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
            padding: 8px 0;
            border-bottom: 1px solid #e2e8f0;
            margin-bottom: 12px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 10px;
        }}
        .meta-label {{
            color: #64748b;
            font-size: 8.5px;
            text-transform: uppercase;
            display: block;
        }}
        .meta-val {{
            font-weight: 700;
            color: #0f172a;
        }}
        .status-box {{
            padding: 10px 14px;
            border-radius: 8px;
            margin-bottom: 12px;
            {status_theme}
        }}
        .section-title {{
            font-size: 10.5px;
            font-weight: 700;
            text-transform: uppercase;
            color: #334155;
            margin: 12px 0 6px 0;
            letter-spacing: 0.5px;
            border-bottom: 1px solid #e2e8f0;
            padding-bottom: 3px;
        }}
        table.data-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 10px;
            font-size: 10px;
        }}
        table.data-table th, table.data-table td {{
            border: 1px solid #e2e8f0;
            padding: 5px 8px;
            text-align: left;
        }}
        table.data-table th {{
            background: #f8fafc;
            color: #475569;
            width: 25%;
            font-weight: 600;
        }}
        .qr-section {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-top: 2px solid #0f172a;
            padding-top: 10px;
            margin-top: 14px;
        }}
        .legal-notice {{
            margin-top: 10px;
            font-size: 7.5px;
            color: #64748b;
            line-height: 1.35;
            text-align: justify;
        }}
    </style>
</head>
<body>
    <div class="cert-container">
        <div class="watermark">{_('SYNTHETIC DEMO • NOT OFFICIAL')}</div>

        <div class="header">
            <div style="font-size: 9px; font-weight: 700; text-transform: uppercase; color: #475569;">
                {_("People's Republic of Bangladesh • LandTech 2026 P3 Track")}
            </div>
            <div class="title">{_('LANDGUARD AI — STATUTORY VERIFICATION REPORT')}</div>
            <div style="font-size: 9px; color: #64748b;">
                {_('Issued under the Statutory Land Verification & Evidence Framework (Registration Act 1908 s.47 / SAT Act s.143)')}
            </div>
            <div class="disclaimer-pill">{_('SYNTHETIC DEMO — NOT AN OFFICIAL LEGAL TITLE CERTIFICATE')}</div>
        </div>

        <div class="meta-grid">
            <div>
                <span class="meta-label">{_('Certificate ID')}</span>
                <span class="meta-val">{v_id}</span>
            </div>
            <div>
                <span class="meta-label">{_('Deed Reference')}</span>
                <span class="meta-val">{verification_record.get('deed_number', 'N/A')}</span>
            </div>
            <div>
                <span class="meta-label">{_('Cadastral Dag Plot')}</span>
                <span class="meta-val">#{verification_record.get('dag_plot_number', 'N/A')}</span>
            </div>
            <div>
                <span class="meta-label">{_('Date of Audit')}</span>
                <span class="meta-val">{issued_at[:10]}</span>
            </div>
        </div>

        <div class="status-box">
            <div style="font-size: 9px; font-weight: 700; text-transform: uppercase; opacity: 0.85;">
                {_('Statutory Verification Verdict')} &bull; {_('Lifecycle:')} {_((report_status or 'VALID').upper())}
            </div>
            <div style="font-size: 15px; font-weight: 800; margin: 2px 0;">{status_title}</div>
            <div style="font-size: 10px; opacity: 0.9;">{status_sub}</div>
        </div>

        <div class="section-title">{_('1. INSTRUMENT & CADASTRAL LINKAGE SCHEDULE')}</div>
        <table class="data-table">
            <tr>
                <th>{_('Deed Instrument No:')}</th><td><strong>{verification_record.get('deed_number', 'N/A')}</strong></td>
                <th>{_('Execution Date:')}</th><td>{verification_record.get('execution_date', 'N/A')}</td>
            </tr>
            <tr>
                <th>{_('Dag Plot Number:')}</th><td><strong style="color: #0284c7;">#{verification_record.get('dag_plot_number', 'N/A')}</strong></td>
                <th>{_('Khatian Number:')}</th><td>#{verification_record.get('khatian_number') or parcel.get('khatian_number') or 'N/A'}</td>
            </tr>
            <tr>
                <th>{_('Transferred Area:')}</th><td><strong>{verification_record.get('transferred_area_decimal', '0')} {_('Decimal')}</strong></td>
                <th>{_('Jurisdiction (Mouza):')}</th><td>{mouza}, {upazila}, {district}</td>
            </tr>
            <tr>
                <th>{_('Vendor NID (Masked):')}</th><td><span style="font-family: monospace;">{masked_seller}</span></td>
                <th>{_('Purchaser NID (Masked):')}</th><td><span style="font-family: monospace;">{masked_buyer}</span></td>
            </tr>
        </table>

        <div class="section-title">{_('2. ALGORITHMIC RISK & FORENSIC VISION SIGNALS')}</div>
        <table class="data-table">
            <tr>
                <th>{_('XGBoost ML Risk Metric')}</th><td><strong>{ml_pct}</strong> ({ml_eval})</td>
                <th>{_('CV Visual Anomaly Score')}</th><td>{cv_pct} ({_('Seam / Whiteout Detection')})</td>
            </tr>
            <tr>
                <th>{_('Registry Seal Status:')}</th><td>{seal_status}</td>
                <th>{_('Sub-Registrar Signature')}</th><td>{sig_status}</td>
            </tr>
        </table>

        <div class="section-title">{_('3. STATUTORY RULE ENGINE EVALUATION LOG')}</div>
        {rules_html}

        {human_det_html}

        <div class="qr-section">
            <div style="display: flex; align-items: center; gap: 12px;">
                <img src="data:image/png;base64,{qr_b64}" style="width: 70px; height: 70px; border: 1px solid #cbd5e1; border-radius: 4px;" alt="QR Code" />
                <div style="font-size: 8.5px; font-family: 'JetBrains Mono', monospace;">
                    <div style="font-weight: 700; color: #0f172a; text-transform: uppercase;">{_('Authenticity QR')}</div>
                    <div style="color: #64748b; margin-top: 1px;">{v_id}</div>
                    <div style="color: #64748b; max-width: 260px; margin-top: 2px;">{_('Scan to inspect live statutory dossier')}</div>
                    <div style="color: #0284c7; font-size: 8px; margin-top: 2px;">{clean_base}/verify/public/{v_id}</div>
                </div>
            </div>

            <div style="flex: 1; margin: 0 16px;">
                <div style="font-size: 8px; font-weight: 700; color: #64748b; text-transform: uppercase;">{_('SHA-256 Cryptographic Evidence Integrity Hash:')}</div>
                <div style="background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 4px; padding: 4px 6px; font-size: 8px; font-family: monospace; word-break: break-all; margin-top: 2px;">
                    {sha256_hash}
                </div>
            </div>

            <div style="text-align: right; min-width: 130px;">
                <div style="width: 130px; border-bottom: 1.5px solid #0f172a; margin-bottom: 4px; margin-left: auto;"></div>
                <div style="font-size: 9.5px; font-weight: 700; text-transform: uppercase;">{_('SENIOR REGISTRAR')}</div>
                <div style="font-size: 8px; color: #64748b;">{_('LandGuard Statutory Engine')}</div>
            </div>
        </div>

        <div class="legal-notice">
            <strong>{_('STATUTORY NOTICE & SCIENTIFIC BENCHMARK DISCLAIMER:')}</strong>
            {_('This document is an algorithmic audit report generated for scientific research and evaluation purposes under the Evidence Act statutory verification framework.')}
            {_('All land parcel boundaries, mouza names, registry seals, and party identities are synthetically generated for benchmark evaluation.')}
            {_('Pursuant to the Evidence Act 1872 s.45 and Registration Act 1908 s.58–60, computer vision and machine learning outputs constitute rebuttable decision-support evidence and do not replace physical parchment examination or judicial title determination.')}
        </div>
    </div>
</body>
</html>"""
    return html


def _generate_pdf_via_headless_browser(
    verification_record: Dict[str, Any],
    base_url: Optional[str] = None,
    lang: str = "bn",
    browser_exe: Optional[str] = None,
) -> Optional[bytes]:
    """Renders authentic PDF with native HarfBuzz Indic glyph shaping via headless Chromium."""
    exe = browser_exe or _find_browser_executable()
    if not exe:
        return None

    html_content = _build_dossier_html(verification_record, base_url=base_url, lang=lang)

    with tempfile.TemporaryDirectory() as td:
        in_html = os.path.join(td, "dossier.html")
        out_pdf = os.path.join(td, "dossier.pdf")
        with open(in_html, "w", encoding="utf-8") as f:
            f.write(html_content)

        cmd = [
            exe,
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={out_pdf}",
            in_html,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        if res.returncode == 0 and os.path.isfile(out_pdf):
            with open(out_pdf, "rb") as pf:
                return pf.read()
    return None


def _generate_verification_pdf_reportlab(
    verification_record: Dict[str, Any],
    base_url: Optional[str] = None,
    lang: str = "bn",
) -> bytes:
    """ReportLab fallback generator. Registers Nirmala TrueType font if available for Unicode safety."""
    target_lang = lang if lang in ["en", "bn"] else "bn"
    _ = lambda k: translate(k, target_lang)

    font_regular = "Helvetica"
    font_bold = "Helvetica-Bold"

    # Try registering Nirmala UI font on Windows
    nirmala_path = r"C:\Windows\Fonts\Nirmala.ttf"
    nirmala_b_path = r"C:\Windows\Fonts\NirmalaB.ttf"
    if os.path.exists(nirmala_path):
        try:
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            pdfmetrics.registerFont(TTFont("Nirmala", nirmala_path))
            if os.path.exists(nirmala_b_path):
                pdfmetrics.registerFont(TTFont("Nirmala-Bold", nirmala_b_path))
            else:
                pdfmetrics.registerFont(TTFont("Nirmala-Bold", nirmala_path))
            font_regular = "Nirmala"
            font_bold = "Nirmala-Bold"
        except Exception:
            pass

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#0F172A"),
        alignment=1,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName=font_regular,
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#475569"),
        alignment=1,
    )
    disclaimer_banner_style = ParagraphStyle(
        "DisclaimerBanner",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#DC2626"),
        alignment=1,
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#1E293B"),
    )
    body_style = ParagraphStyle(
        "DocBody",
        parent=styles["Normal"],
        fontName=font_regular,
        fontSize=7.5,
        leading=10.5,
        textColor=colors.HexColor("#334155"),
    )
    bold_label = ParagraphStyle(
        "BoldLabel",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=7.5,
        leading=10.5,
        textColor=colors.HexColor("#0F172A"),
    )
    code_style = ParagraphStyle(
        "CodeText",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=6.5,
        leading=8.5,
        textColor=colors.HexColor("#0F172A"),
    )

    story = []

    story.append(Paragraph(_("GOVERNMENT OF THE PEOPLE'S REPUBLIC OF BANGLADESH"), subtitle_style))
    story.append(Paragraph(_("MINISTRY OF LAND • LAND REGISTRATION REFORM INITIATIVE"), subtitle_style))
    story.append(Paragraph(_("LANDGUARD STATUTORY VERIFICATION DOSSIER"), title_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(_("SYNTHETIC DEMO — NOT AN OFFICIAL LEGAL TITLE CERTIFICATE"), disclaimer_banner_style))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284C7"), spaceAfter=10))

    v_id = verification_record.get("verification_id", "VRF-UNKNOWN")
    issued_at = verification_record.get("timestamp") or datetime.datetime.now().isoformat()
    overall_status = verification_record.get("overall_status", "PENDING")
    report_status = (verification_record.get("report_status") or "VALID").upper()

    if report_status == "WITHDRAWN":
        verdict_bg = colors.HexColor("#FEE2E2")
        verdict_text_color = colors.HexColor("#991B1B")
        verdict_border = colors.HexColor("#DC2626")
        status_display = _("CERTIFICATE FORMALLY WITHDRAWN & REVOKED")
    elif report_status == "SUPERSEDED":
        verdict_bg = colors.HexColor("#FEF3C7")
        verdict_text_color = colors.HexColor("#92400E")
        verdict_border = colors.HexColor("#F59E0B")
        status_display = _("CERTIFICATE SUPERSEDED BY REVISED DETERMINATION")
    elif overall_status == "CLEAR_FOR_STANDARD_PROCESSING":
        verdict_bg = colors.HexColor("#ECFDF5")
        verdict_text_color = colors.HexColor("#065F46")
        verdict_border = colors.HexColor("#10B981")
        status_display = _("CLEAR FOR STANDARD PROCESSING")
    elif overall_status == "MISSING_EVIDENCE":
        verdict_bg = colors.HexColor("#FEF3C7")
        verdict_text_color = colors.HexColor("#92400E")
        verdict_border = colors.HexColor("#F59E0B")
        status_display = _("MISSING EVIDENCE / UNINDEXED ARCHIVE")
    else:
        verdict_bg = colors.HexColor("#FEE2E2")
        verdict_text_color = colors.HexColor("#991B1B")
        verdict_border = colors.HexColor("#DC2626")
        status_display = _("CONFIRMED STATUTORY CONTRADICTION")

    status_table_data = [
        [
            Paragraph(f"<b>{_('Statutory Verification Verdict')}</b> &bull; {_('Lifecycle:')} {_(report_status)}", bold_label),
            Paragraph(f"<b>{_('Certificate ID')}:</b> {v_id}", bold_label),
        ],
        [
            Paragraph(f"<font color='{verdict_text_color.hexval()}'><b>{status_display}</b></font>", ParagraphStyle("VBig", parent=title_style, fontSize=11, leading=14, textColor=verdict_text_color, alignment=0)),
            Paragraph(f"<b>{_('Date of Audit')}:</b> {issued_at[:10]}", body_style),
        ],
    ]
    status_table = Table(status_table_data, colWidths=[360, 180])
    status_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), verdict_bg),
        ("BOX", (0, 0), (-1, -1), 1.5, verdict_border),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(status_table)
    story.append(Spacer(1, 10))

    # Instrument Schedule
    story.append(Paragraph(_("1. INSTRUMENT & CADASTRAL LINKAGE SCHEDULE"), section_heading))
    story.append(Spacer(1, 4))

    parcel = verification_record.get("cadastral_parcel") or {}
    mouza = parcel.get("mouza") or verification_record.get("mouza") or "N/A"
    upazila = parcel.get("upazila") or verification_record.get("upazila") or "N/A"
    district = parcel.get("district") or verification_record.get("district") or "N/A"

    inst_data = [
        [
            Paragraph(f"<b>{_('Deed Instrument No:')}</b>", bold_label),
            Paragraph(str(verification_record.get("deed_number", "N/A")), body_style),
            Paragraph(f"<b>{_('Execution Date:')}</b>", bold_label),
            Paragraph(str(verification_record.get("execution_date", "N/A")), body_style),
        ],
        [
            Paragraph(f"<b>{_('Dag Plot Number:')}</b>", bold_label),
            Paragraph(f"#{verification_record.get('dag_plot_number', 'N/A')}", body_style),
            Paragraph(f"<b>{_('Khatian Number:')}</b>", bold_label),
            Paragraph(f"#{verification_record.get('khatian_number') or parcel.get('khatian_number') or 'N/A'}", body_style),
        ],
        [
            Paragraph(f"<b>{_('Transferred Area:')}</b>", bold_label),
            Paragraph(f"{verification_record.get('transferred_area_decimal', '0')} {_('Decimal')}", body_style),
            Paragraph(f"<b>{_('Jurisdiction (Mouza):')}</b>", bold_label),
            Paragraph(f"{mouza}, {upazila}, {district}", body_style),
        ],
    ]
    inst_table = Table(inst_data, colWidths=[120, 150, 120, 150])
    inst_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(inst_table)
    story.append(Spacer(1, 10))

    # Signals
    story.append(Paragraph(_("2. ALGORITHMIC RISK & FORENSIC VISION SIGNALS"), section_heading))
    story.append(Spacer(1, 4))
    ml_score = verification_record.get("ml_risk_score", 0.0)
    ml_pct = f"{float(ml_score)*100:.2f}%" if ml_score is not None else "N/A"
    cv_ev = verification_record.get("cv_evidence") or {}
    cv_anom = cv_ev.get("visual_anomaly_score", 0.0)
    cv_pct = f"{float(cv_anom)*100:.1f}%" if cv_anom is not None else "N/A"

    signals_data = [
        [
            Paragraph(f"<b>{_('XGBoost ML Risk Metric')}</b>", bold_label),
            Paragraph(f"{ml_pct}", body_style),
            Paragraph(f"<b>{_('CV Visual Anomaly Score')}</b>", bold_label),
            Paragraph(f"{cv_pct} ({_('Seam / Whiteout Detection')})", body_style),
        ],
    ]
    signals_table = Table(signals_data, colWidths=[130, 140, 130, 140])
    signals_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(signals_table)
    story.append(Spacer(1, 10))

    # Rules
    story.append(Paragraph(_("3. STATUTORY RULE ENGINE EVALUATION LOG"), section_heading))
    story.append(Spacer(1, 4))
    rules = verification_record.get("rules_triggered", [])
    if not rules:
        no_rules_p = Paragraph(
            f"<b>{_('Clean Statutory Audit:')}</b> {_('No configured statutory contradictions triggered during algorithmic evaluation against registered cadastral ledgers.')}",
            body_style,
        )
        nr_table = Table([[no_rules_p]], colWidths=[540])
        nr_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ECFDF5")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#10B981")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(nr_table)
    else:
        rule_rows = [
            [
                Paragraph(f"<b>{_('Rule Code / Statutory Reference')}</b>", bold_label),
                Paragraph(f"<b>{_('Category / Severity')}</b>", bold_label),
                Paragraph(f"<b>{_('Explanation & Next Step')}</b>", bold_label),
            ]
        ]
        for r in rules:
            code = r.get("rule_code", "STATUTORY_RULE")
            meta = RULE_METADATA.get(code, {})
            title = r.get("title_bn") if (target_lang == "bn" and r.get("title_bn")) else (meta.get("title_bn") if target_lang == "bn" else _(r.get("title") or code))
            stat_ref = r.get("statutory_reference") or meta.get("statutory_reference") or "Registration Act 1908"
            sev = _(r.get("severity", "HIGH"))
            if target_lang == "bn":
                expl = r.get("explanation_bn") or meta.get("default_explanation_bn") or _(r.get("explanation") or r.get("reason", ""))
            else:
                expl = _(r.get("explanation") or r.get("reason", ""))
            rule_rows.append([
                Paragraph(f"<b>{title}</b><br/><font color='#64748B'>{code}</font><br/><font color='#0284C7'>{stat_ref}</font>", body_style),
                Paragraph(f"<b>{sev}</b>", body_style),
                Paragraph(expl, body_style),
            ])
        rules_table = Table(rule_rows, colWidths=[170, 90, 280])
        rules_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(rules_table)

    story.append(Spacer(1, 10))

    # Cryptographic proof & QR
    story.append(Paragraph(_("5. CRYPTOGRAPHIC INTEGRITY & VERIFICATION QR"), section_heading))
    story.append(Spacer(1, 4))
    sha256_hash = verification_record.get("sha256_hash") or verification_record.get("sha256_certificate_hash", "UNCOMPUTED")
    clean_base = get_public_base_url(base_url)
    qr_bytes = generate_verification_qr(v_id, base_url=clean_base, box_size=4, border=1)
    qr_img = RLImage(io.BytesIO(qr_bytes), width=75, height=75)
    qr_text = (
        f"<b>{_('CANONICAL RECORD SHA-256 DIGEST:')}</b><br/>"
        f"<font color='#0F172A'>{sha256_hash}</font><br/><br/>"
        f"<b>{_('PUBLIC VERIFICATION URL:')}</b><br/>"
        f"{clean_base}/verify/public/{v_id}<br/>"
        f"<font color='#64748B'>{_('Scan to inspect live statutory dossier')}</font>"
    )
    qr_table = Table([[qr_img, Paragraph(qr_text, code_style)]], colWidths=[85, 455])
    qr_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(qr_table)
    story.append(Spacer(1, 10))

    legal_p = Paragraph(
        f"<b>{_('STATUTORY NOTICE & SCIENTIFIC BENCHMARK DISCLAIMER:')}</b> "
        f"{_('This document is an algorithmic audit report generated for scientific research and evaluation purposes under the Evidence Act statutory verification framework.')} "
        f"{_('All land parcel boundaries, mouza names, registry seals, and party identities are synthetically generated for benchmark evaluation.')}",
        ParagraphStyle("LegalDisclaimer", parent=body_style, fontSize=6.5, leading=9, textColor=colors.HexColor("#64748B")),
    )
    story.append(legal_p)

    doc.build(story)
    return buffer.getvalue()


def generate_verification_pdf(
    verification_record: Dict[str, Any],
    base_url: Optional[str] = None,
    lang: str = "bn",
) -> bytes:
    """
    Renders an authoritative, tamper-evident PDF dossier for a verification record.
    Supports English ('en') and Bengali ('bn') with HarfBuzz complex Indic glyph shaping
    via headless browser rendering, falling back to ReportLab.
    Returns the binary PDF content as bytes.
    """
    target_lang = lang if lang in ["en", "bn"] else "bn"

    # 1. Attempt Headless Chrome/Edge rendering (Full HarfBuzz Unicode & Google Fonts support)
    browser_exe = _find_browser_executable()
    if browser_exe:
        try:
            pdf_bytes = _generate_pdf_via_headless_browser(
                verification_record=verification_record,
                base_url=base_url,
                lang=target_lang,
                browser_exe=browser_exe,
            )
            if pdf_bytes and len(pdf_bytes) > 1000:
                return pdf_bytes
        except Exception as e:
            print(f"[PDF Generator] Warning: Headless browser rendering failed ({e}), falling back to ReportLab.")

    # 2. Fallback to ReportLab generator
    return _generate_verification_pdf_reportlab(
        verification_record=verification_record,
        base_url=base_url,
        lang=target_lang,
    )
