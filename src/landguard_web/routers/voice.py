"""LandGuard Voice Router
Bilingual English & Bengali Voice Assistant interface and speech intent parsing.
"""

from typing import Optional
from fastapi import APIRouter, Request, HTTPException, Response, Query
from fastapi.responses import HTMLResponse, JSONResponse

from src.landguard_web.dependencies import templates, require_citizen_access
from src.landguard_web.schemas import VoiceIntentRequest
from src.landguard_web.rate_limiter import check_rate_limit

router = APIRouter(tags=["voice"])


@router.get("/user/voice", response_class=HTMLResponse)
async def citizen_voice(request: Request):
    """Bilingual Bangla and English Voice Assistant interface with speech-to-text and intent execution."""
    user = require_citizen_access(request)
    return templates.TemplateResponse(
        request=request,
        name="user/voice.html",
        context={
            "current_user": user,
            "active_page": "voice",
        },
    )


@router.post("/api/voice/parse-intent")
async def parse_voice_intent_endpoint(req: VoiceIntentRequest, request: Request):
    """Parses bilingual English & Bengali voice transcripts into structured intents and actions."""
    check_rate_limit(request, "voice_intent", max_requests=30, window_seconds=60)
    from src.landguard_ai.voice_assistant import parse_bilingual_intent
    from src.landguard_web.dependencies import get_current_user
    from src.landguard_web.localization import get_preferred_language
    from src.landguard_web.service import service

    current_user = get_current_user(request)
    site_lang = get_preferred_language(request, current_user)

    result = parse_bilingual_intent(
        req.text,
        language_preference=req.language,
        registry_lookup_fn=service.get_parcel_details,
        complaint_lookup_fn=service.get_complaint,
        deed_lookup_fn=service.lookup_deed,
        current_user=current_user,
    )
    result["site_language"] = site_lang
    return JSONResponse(status_code=200, content=result)


@router.get("/api/voice/tts")
async def voice_text_to_speech(
    request: Request,
    text: str = Query(..., min_length=1, max_length=500),
    lang: Optional[str] = Query(None),
):
    """High-fidelity Neural Text-To-Speech for authentic Bangladeshi Bengali & US English female voices.

    Bengali Female: bn-BD-NabanitaNeural
    English Female: en-US-AriaNeural
    """
    check_rate_limit(request, "voice_tts", max_requests=20, window_seconds=60)
    cleaned = text.strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail="Text parameter cannot be empty")

    from src.landguard_web.localization import get_preferred_language
    from src.landguard_web.dependencies import get_current_user

    if not lang or lang not in ["bn", "en"]:
        current_user = get_current_user(request)
        lang = get_preferred_language(request, current_user)

    try:
        from src.landguard_services.voice_service import VoiceService
        voice_service = VoiceService()
        audio_bytes = await voice_service.synthesize_speech(cleaned, lang=lang)
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Cache-Control": "public, max-age=3600",
                "Content-Disposition": "inline",
                "Accept-Ranges": "bytes",
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"TTS synthesis error: {str(exc)}")

