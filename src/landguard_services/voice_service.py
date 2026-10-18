import io
from typing import Dict, Any, Optional

try:
    import edge_tts
except ImportError:
    edge_tts = None

from src.landguard_ai.voice_assistant import (
    parse_bilingual_intent,
    to_en_digits,
    to_bn_digits,
    detect_language,
    extract_entities,
)

BANGLA_FEMALE_VOICE = "bn-BD-NabanitaNeural"
ENGLISH_FEMALE_VOICE = "en-US-AriaNeural"


class VoiceService:
    """Domain service managing conversational speech-to-intent resolution and neural speech synthesis."""

    def parse_intent(
        self,
        transcript: str,
        language_preference: Optional[str] = "auto",
        registry_lookup_fn: Optional[Any] = None,
        complaint_lookup_fn: Optional[Any] = None,
        deed_lookup_fn: Optional[Any] = None,
        current_user: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Parses speech transcript into structured intent and actionable response."""
        return parse_bilingual_intent(
            transcript,
            language_preference=language_preference,
            registry_lookup_fn=registry_lookup_fn,
            complaint_lookup_fn=complaint_lookup_fn,
            deed_lookup_fn=deed_lookup_fn,
            current_user=current_user,
        )

    def normalize_digits(self, text: str) -> str:
        """Converts Bengali numerals to standard ASCII digits."""
        return to_en_digits(text)

    def to_bengali_digits(self, text: str) -> str:
        """Converts ASCII digits to Bengali numerals."""
        return to_bn_digits(text)

    def detect_lang(self, text: str) -> str:
        """Detects language ('bn' or 'en') from text."""
        return detect_language(text)

    def extract_entities(self, text: str) -> Dict[str, Any]:
        """Extracts plot numbers, deed numbers, and IDs from query text."""
        return extract_entities(text)

    async def synthesize_speech(self, text: str, lang: str = "bn") -> bytes:
        """Synthesizes high-fidelity speech audio using neural female voices.

        Bengali: bn-BD-NabanitaNeural (Bangladeshi female neural voice)
        English: en-US-AriaNeural (US English female neural voice)
        """
        cleaned_text = (text or "").strip()
        if not cleaned_text:
            raise ValueError("Text parameter cannot be empty for speech synthesis")
        if not edge_tts:
            raise RuntimeError("Neural TTS service requires edge-tts package to be installed")

        voice = BANGLA_FEMALE_VOICE if (lang == "bn" or str(lang).lower().startswith("bn")) else ENGLISH_FEMALE_VOICE
        communicate = edge_tts.Communicate(cleaned_text, voice)
        mp3_buffer = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk.get("type") == "audio":
                mp3_buffer.write(chunk.get("data", b""))
        mp3_buffer.seek(0)
        audio_data = mp3_buffer.read()
        if not audio_data:
            raise RuntimeError("Neural TTS yielded empty audio buffer")
        return audio_data

