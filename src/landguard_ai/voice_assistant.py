"""LandGuard Bilingual Voice & Conversational Assistant Engine.
Provides deterministic intent parsing, entity extraction, and bilingual readback responses
for both Bengali (Bangla) and English queries covering:
1. Cadastral plot searches and chain of title lookups.
2. Verification dossier status and fraud risk assessments.
3. Citizen complaint drafting with mandatory confirmation readbacks.
4. Expedited hearing inquiries and system help.
"""

import re
from typing import Dict, Any, Optional, Tuple

_BN_TO_EN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
_EN_TO_BN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")

_EN_WORD_DIGITS = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
}
_BN_WORD_DIGITS = {
    "শূণ্য": "0", "শূন্য": "0", "জিরো": "0",
    "ওয়ান": "1", "টু": "2", "থ্রি": "3", "ফোর": "4",
    "ফাইভ": "5", "সিক্স": "6", "সেভেন": "7", "এইট": "8", "নাইন": "9",
}

_GREETING_WORDS = r"(?:hell?o+w?|hallo|hey|hi|hai|হ্যালো|হেলো|হাই|হে)"
_DAFFODIL_WORDS = (
    r"(?:daff?od[ia]ll?|deff?od[ia]ll?|deafod[ia]ll?|defa[u]?lt?|"
    r"ড্যাফোডিল|ডেফোডিল|ডাফোডিল|ডেফডিল|ড্যাফডিল|দেফোডিল|দ্যাফোডিল|ড্যাফোডেল|ডেফোডেল|ড্যাপোডিল|ডেপোডিল|ড্যাফুডিল|ডিফোডিল|ডিফডিল)"
)

WAKE_WORD_PATTERNS = [
    # Full compound wake phrases: greeting + daffodil in English, Bengali, or mixed
    rf"(?:^|[^\u0980-\u09FFa-zA-Z0-9]){_GREETING_WORDS}[\s,.:;!?-]+{_DAFFODIL_WORDS}(?:$|[^\u0980-\u09FFa-zA-Z0-9])",
    # Standalone daffodil
    rf"(?:^|[^\u0980-\u09FFa-zA-Z0-9]){_DAFFODIL_WORDS}(?:$|[^\u0980-\u09FFa-zA-Z0-9])",
]


def strip_wake_word(text: str) -> Tuple[bool, str]:
    """Detects 'Hello Daffodil' wake phrase and returns (is_detected, cleaned_command)."""
    if not text:
        return False, ""
    cleaned = text.strip()
    detected = False
    for pat in WAKE_WORD_PATTERNS:
        if re.search(pat, cleaned, re.IGNORECASE):
            detected = True
            cleaned = re.sub(pat, " ", cleaned, flags=re.IGNORECASE).strip()
            cleaned = re.sub(r"^[,\s:;!?-]+|[,\s:;!?-]+$", "", cleaned).strip()
    return detected, cleaned


def to_en_digits(text: str) -> str:
    """Normalizes Bengali numerals and spoken number words to standard Western ASCII digits."""
    trans = (text or "").translate(_BN_TO_EN_DIGITS)
    tokens = trans.split()
    normalized_tokens = []
    for token in tokens:
        clean = token.strip(".,:;?!-()\"'").lower()
        if clean in _EN_WORD_DIGITS:
            normalized_tokens.append(_EN_WORD_DIGITS[clean])
        elif clean in _BN_WORD_DIGITS:
            normalized_tokens.append(_BN_WORD_DIGITS[clean])
        else:
            normalized_tokens.append(token)
    collapsed = " ".join(normalized_tokens)
    # Collapse whitespace between adjacent digits e.g. "9 0 4 4" -> "9044"
    return re.sub(r"(?<=\d)\s+(?=\d)", "", collapsed)


def to_bn_digits(text: str) -> str:
    """Converts Western ASCII digits to Bengali numerals."""
    return text.translate(_EN_TO_BN_DIGITS)


_BN_TO_EN_PHONETIC_COMMANDS = {
    # Pronouns & Conversational Auxiliaries
    r"\bমাই\b": "My",
    r"\bনেম\b": "name",
    r"\bইজ\b": "is",
    r"\bইস\b": "is",
    r"\bহোয়াট\b": "What",
    r"\bহোয়াট\b": "What",
    r"\bহোট\b": "What",
    r"\bদ্য\b": "the",
    r"\bদি\b": "the",
    r"\bদা\b": "the",
    r"\bঅফ\b": "of",
    r"\bঅব\b": "of",
    r"\bহু\b": "Who",
    r"\bওনার\b": "owner",
    r"\bহাউ\b": "How",
    r"\bআর\b": "are",
    r"\bইউ\b": "you",
    r"\bদিস\b": "this",
    r"\bদ্যাট\b": "that",
    r"\bআই\b": "I",
    r"\bওয়ান্ট\b": "want",
    r"\bওয়ান্ট\b": "want",
    r"\bটু\b": "to",
    r"\bসি\b": "see",
    r"\bশো\b": "Show",
    r"\bমি\b": "me",
    r"\bগিভ\b": "Give",
    r"\bটেল\b": "Tell",
    r"\bপ্লিজ\b": "Please",
    r"\bহেল্প\b": "Help",
    r"\bহ্যালো\b": "Hello",
    r"\bহেলো\b": "Hello",
    r"\bহাই\b": "Hi",
    r"\bগুড\b": "Good",
    r"\bমর্নিং\b": "Morning",
    r"\bথ্যাংকস\b": "Thanks",
    r"\bথ্যাংক\s*ইউ\b": "Thank you",
    r"\bথ্যাংক\b": "Thank",
    r"\bইয়েস\b": "Yes",
    r"\bনো\b": "No",
    r"\bওকে\b": "Okay",
    r"\bক্যান\b": "Can",
    r"\bএবাউট\b": "about",

    # Commands & Land Terms
    r"\bফাইন্ড\b": "Find",
    r"\bসার্চ\b": "Search",
    r"\bচেক\b": "Check",
    r"\bলুকআপ\b": "Lookup",
    r"\bভেরিফাই\b": "Verify",
    r"\bভেরিফিকেশন\b": "Verification",
    r"\bকমপ্লেইন্ট?\b": "Complaint",
    r"\bকমপ্লেন\b": "Complaint",
    r"\bকমপ্লেইন\b": "Complaint",
    r"\bস্ট্যাটাস\b": "Status",
    r"\bস্টেটাস\b": "Status",
    r"\bষ্ট্যাটাস\b": "Status",
    r"\bস্টাটাস\b": "Status",
    r"\bপ্লট\b": "Plot",
    r"\bহোল্ডিং\b": "Holding",
    r"\bপার্সেল\b": "Parcel",
    r"\bডিড\b": "Deed",
    r"\bডীড\b": "Deed",
    r"\bডকুমেন্ট\b": "Document",
    r"\bরেকর্ড\b": "Record",
    r"\bসেফ\b": "Safe",
    r"\bফাইল\b": "File",
    r"\bডিটেইলস\b": "Details",
    r"\bডিটেলস\b": "Details",
    r"\bইনফরমেশন\b": "Information",
    r"\bইনফো\b": "Info",
    r"\bনাম্বার\b": "Number",
    r"\bনাম্বর\b": "Number",
    r"\bকেস\b": "Case",
    r"\bরিপোর্ট\b": "Report",
    r"\bলিগ্যাল\b": "Legal",
    r"\bলিগাল\b": "Legal",
    r"\bক্লিয়ার\b": "Clear",
    r"\bক্লিয়ার\b": "Clear",
    r"\bভিউ\b": "View",
    r"\bওপেন\b": "Open",
    r"\bআশিক\b": "Aashiq",
    r"\bড্যাশবোর্ড\b": "Dashboard",
    r"\bড্যাসবোর্ড\b": "Dashboard",
    r"\bড্যাশবর্ড\b": "Dashboard",
    r"\bদেশবোর্ড\b": "Dashboard",
    r"\bহিস্ট্রি\b": "History",
    r"\bহিস্টোরি\b": "History",
    r"\bনোটিফিকেশন\b": "Notifications",
    r"\bনোটিফিকেশনস\b": "Notifications",
    r"\bসেটিংস\b": "Settings",
    r"\bসেটিং\b": "Settings",
    r"\bপ্রোফাইল\b": "Profile",
    r"\bপ্রফাইল\b": "Profile",
    r"\bড্যাফোডিল\b": "Daffodil",
    r"\bডেফোডিল\b": "Daffodil",
    r"\bডাফোডিল\b": "Daffodil",
    r"\bডেফডিল\b": "Daffodil",
    r"\bস্টপ\b": "Stop",
    r"\bব্যাক\b": "Back",
}


def normalize_transliterated_english(text: str) -> str:
    """Normalizes Bengali-script phonetically transliterated English speech commands into English words.
    e.g. 'ফাইন্ড 404' -> 'Find 404', 'সার্চ 9044' -> 'Search 9044', 'মাই নেম ইজ আশিক' -> 'My name is Aashiq'.
    Preserves genuine Bengali sentences containing Bengali grammatical markers.
    """
    if not text:
        return ""
    has_bengali_grammar = bool(
        re.search(
            r"\b(এর|কি|কী|কে|কার|তথ্য|দিন|করুন|চাই|আছে|কোথায়|কোথায়|সম্পর্কে|বলুন|অভিযোগ|মামলা|জালিয়াতি|খতিয়ান|খতিয়ান|মালিক|জমি|নিরাপদ|বর্তমান|অবস্থা|যাচাই|নথি|আমার|আমাদের|আপনার|দাগ|দেখাও|দেখান|যাও|খুলুন|করো|কর)\b",
            text,
        )
    )
    if has_bengali_grammar:
        return text

    normalized = text
    matches = 0
    for pat, repl in _BN_TO_EN_PHONETIC_COMMANDS.items():
        if re.search(pat, normalized, re.IGNORECASE):
            matches += 1
            normalized = re.sub(pat, repl, normalized, flags=re.IGNORECASE)

    if matches > 0:
        normalized = to_en_digits(normalized)
        return normalized.strip()

    return text


ROMANIZED_BN_STRONG_WORDS: Dict[str, str] = {
    # Pronouns & Greetings
    "amar": "আমার", "amr": "আমার", "aman": "আমার", "amaar": "আমার",
    "amader": "আমাদের", "amaderke": "আমাদের",
    "apnar": "আপনার", "apnr": "আপনার", "apnader": "আপনার",
    "tumi": "তুমি", "apni": "আপনি", "ami": "আমি", "aami": "আমি",
    "ashik": "আশিক", "aashiq": "আশিক", "asik": "আশিক", "ashique": "আশিক",
    "kemon": "কেমন", "achen": "আছেন", "asen": "আছেন", "aso": "আছো", "acho": "আছো",
    "valo": "ভালো", "bhalo": "ভালো",
    "shunchen": "শুনছেন", "shunun": "শুনুন", "bolun": "বলুন", "bolen": "বলুন",
    
    # Land & Government / Legal Terms
    "dag": "দাগ", "dak": "দাগ", "daag": "দাগ",
    "khotian": "খতিয়ান", "khatian": "খতিয়ান", "khotiyan": "খতিয়ান", "porcha": "পর্চা",
    "jomi": "জমি", "zomi": "জমি", "jomir": "জমির", "zomir": "জমির",
    "tottho": "তথ্য", "totho": "তথ্য", "totto": "তথ্য", "tathya": "তথ্য",
    "din": "দিন", "den": "দিন", "diben": "দিন", "dekhan": "দেখান", "dekhte": "দেখতে", "dekhaw": "দেখাও",
    "obostha": "অবস্থা", "obosta": "অবস্থা",
    "malik": "মালিক", "malikana": "মালিক",
    "dolil": "দলিল", "doleel": "দলিল",
    "ovijog": "অভিযোগ", "obhijog": "অভিযোগ", "ovijug": "অভিযোগ", "obhijug": "অভিযোগ",
    "mamla": "মামলা", "jhamela": "ঝামেলা",
    "jachai": "যাচাই", "bachai": "যাচাই", "jachay": "যাচাই",
    "kothay": "কোথায়", "kothai": "কোথায়", "koi": "কোথায়",
    "chai": "চাই", "cai": "চাই", "lagbe": "লাগবে",
    "mouza": "মৌজা", "mouja": "মৌজা",
    "khujo": "খুঁজুন", "khujun": "খুঁজুন",
    "shob": "সব", "shobai": "সবাই", "ekhon": "এখন",
    "bujhte": "বুঝতে", "bujhi": "বুঝি",
}

ROMANIZED_BN_CONTEXT_WORDS: Dict[str, str] = {
    "nam": "নাম", "naam": "নাম", "name": "নাম",
    "ki": "কী", "kee": "কী", "kio": "কী",
    "ache": "আছে", "ase": "আছে", "nai": "নেই", "nei": "নেই",
    "korun": "করুন", "koren": "করুন", "koro": "করো",
    "er": "এর",
    "plot": "প্লট",
    "number": "নম্বর", "nombor": "নম্বর", "nombar": "নম্বর", "no": "নং",
    "status": "স্ট্যাটাস",
    "info": "তথ্য",
    "details": "বিবরণ",
    "bam": "", "bahut": ""
}

ENGLISH_COMMANDS = set([
    "search", "find", "check", "what", "where", "how", "who", "when", "why",
    "verify", "lookup", "give", "tell", "show", "is", "are", "do", "does",
    "can", "could", "would", "please", "open", "view", "file"
])

EN_DIGITS_TO_BN_TABLE = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")


def normalize_romanized_bengali(text: str) -> str:
    """Normalizes Romanized Bengali phonetics produced by English speech recognition (or user typing)
    into standard Bengali script, e.g.:
    'Aman Naam Aashiq' -> 'আমার নাম আশিক'
    'Amar plot 9044' -> 'আমার প্লট ৯০৪৪'
    'Dag 9044 er totho din' -> 'দাগ ৯০৪৪ এর তথ্য দিন'
    'Jomir obostha ki' -> 'জমির অবস্থা কী'
    'Dak Bam bahut 307' -> 'দাগ ৩০৭'
    Preserves genuine English queries (e.g. 'Search plot 9044', 'What is the status of plot 9044').
    """
    if not text or not text.strip():
        return text

    tokens = text.strip().split()
    lower_tokens = [re.sub(r"[^\w]", "", t).lower() for t in tokens]

    strong_bn_count = sum(1 for t in lower_tokens if t in ROMANIZED_BN_STRONG_WORDS)
    if strong_bn_count == 0:
        return text

    has_english_command = any(t in ENGLISH_COMMANDS for t in lower_tokens)
    if has_english_command and strong_bn_count < 2:
        return text

    new_tokens = []
    for tok, clean in zip(tokens, lower_tokens):
        if clean in ROMANIZED_BN_STRONG_WORDS:
            new_tokens.append(ROMANIZED_BN_STRONG_WORDS[clean])
        elif clean in ROMANIZED_BN_CONTEXT_WORDS:
            repl = ROMANIZED_BN_CONTEXT_WORDS[clean]
            if repl:
                new_tokens.append(repl)
        elif clean.isdigit():
            new_tokens.append(clean)
        else:
            new_tokens.append(tok)

    res = " ".join(new_tokens).strip()
    return res.translate(EN_DIGITS_TO_BN_TABLE)


def detect_language(text: str) -> str:
    """Detects whether query is Bengali or English based on dominant script character count.
    Handles mixed-script phonetic normalizations, Bengali numerals, and Romanized queries accurately.
    """
    if not text:
        return "bn"

    # If text contains Romanized Bengali words (e.g. 'Aman Naam Aashiq' or 'Amar plot 9044'),
    # test if it normalizes into Bengali script
    norm_bn = normalize_romanized_bengali(text)
    if norm_bn != text:
        return "bn"

    latin_chars = len(re.findall(r"[a-zA-Z]", text))
    bn_chars = len(re.findall(r"[\u0980-\u09FF]", text))
    if latin_chars > bn_chars:
        return "en"
    if bn_chars > latin_chars:
        return "bn"
    # Fallback for digits-only queries or neutral text (Bangla is the primary system default)
    if re.search(r"[০-৯]", text):
        return "bn"
    return "bn"


def extract_entities(text: str) -> Dict[str, Any]:
    """Extracts plot numbers, deed numbers, verification IDs, and complaint IDs."""
    norm_text = to_en_digits(text).lower()
    entities = {}

    # Verification ID: e.g. VRF-HIST-001, VRF-20240101-ABCD
    vid_match = re.search(r"\b(VRF-[A-Z0-9_-]+)\b", norm_text, re.IGNORECASE)
    if vid_match:
        entities["verification_id"] = vid_match.group(1).upper()

    # Complaint ID: e.g. CMP-2026-001
    cmp_match = re.search(r"\b(CMP-[A-Z0-9_-]+)\b", norm_text, re.IGNORECASE)
    if cmp_match:
        entities["complaint_id"] = cmp_match.group(1).upper()

    # Deed number:
    # 1. Standard explicit DEED- prefix format (e.g. DEED-2006-18946, DEED-404)
    deed_match = re.search(r"\b(DEED-[A-Z0-9_-]+)\b", norm_text, re.IGNORECASE)
    # 2. Spoken/text prefix format (e.g. 'দলিল নম্বর 404', 'দলিল নং 404', 'দলিল 404', 'deed number 404', 'dolil 404')
    deed_prefix = re.search(
        r"(?:deed|dolil|dalil|দলিল)\s*(?:নং|নম্বর|নাম্বার|number|no\.?|#)?\s*[:#]?\s*([a-z0-9_-]*\d+[a-z0-9_-]*)\b",
        norm_text,
        re.IGNORECASE,
    )
    # 3. Spoken/text suffix format (e.g. '404 নম্বর দলিল', '404 নং দলিল', '404 দলিল', '404 deed')
    deed_suffix = re.search(
        r"\b([a-z0-9_-]*\d+[a-z0-9_-]*)\s*(?:নং\s*|নম্বর\s*|নাম্বার\s*|no\.?\s*|number\s*)?(?:deed|dolil|dalil|দলিল)\b",
        norm_text,
        re.IGNORECASE,
    )
    if deed_match:
        entities["deed_number"] = deed_match.group(1).upper()
    elif deed_prefix:
        entities["deed_number"] = deed_prefix.group(1).upper()
    elif deed_suffix:
        entities["deed_number"] = deed_suffix.group(1).upper()

    # Dag plot number:
    # 1. Prefix: e.g. 'plot 9044', 'dag 9044', 'dak 9044', 'plot no 9044', 'plot no. 9044', 'দাগ ৯০৪৪', 'দাগ নং ৯০৪৪', 'দাগ নম্বর ৯০৪৪'
    plot_prefix = re.search(
        r"(?:plot|dag|dak|parcel|holding|khatian|দাগ|প্লট|খতিয়ান|খতিয়ান)\s*(?:নং|নম্বর|নাম্বার|number|no\.?|#)?\s*[:#]?\s*(\d{1,5})\b",
        norm_text,
        re.IGNORECASE,
    )
    # 2. Suffix: e.g. '9044 dag', '9044 dak', '9044 plot', '9044 no plot', '৯০৪৪ দাগ', '৯০৪৪ নং দাগ', '৯০৪৪ প্লট'
    plot_suffix = re.search(
        r"\b(\d{1,5})\s*(?:নং\s*|নম্বর\s*|নাম্বার\s*|no\.?\s*|number\s*)?(?:dag|dak|plot|parcel|holding|khatian|দাগ|প্লট|খতিয়ান|খতিয়ান)\b",
        norm_text,
        re.IGNORECASE,
    )

    if plot_prefix:
        entities["dag_plot_number"] = plot_prefix.group(1)
    elif plot_suffix:
        entities["dag_plot_number"] = plot_suffix.group(1)
    else:
        # Fallback standalone 3-5 digit number if query has land context or is a direct number query
        standalone = re.search(r"\b([1-9]\d{2,4})\b", norm_text)
        if (
            standalone
            and not entities.get("verification_id")
            and not entities.get("deed_number")
            and not entities.get("complaint_id")
        ):
            land_hints = [
                "জমি", "মালিক", "রেকর্ড", "land", "parcel", "holding", "check", "info", "তথ্য",
                "খতিয়ান", "খতিয়ান", "search", "find", "show", "view", "see", "খুঁজুন", "দেখাও",
                "দেখতে চাই", "সম্পত্তি", "property", "details", "query", "অনুসন্ধান", "প্লট", "দাগ",
                "plot", "dag", "dak", "inspect", "lookup", "safe", "status", "অবস্থা", "নিরাপদ"
            ]
            is_bare_number = bool(re.search(r"^\s*(?:#|no\.?|নং)?\s*[1-9]\d{2,4}\s*$", norm_text))
            if is_bare_number or any(h in norm_text for h in land_hints):
                entities["dag_plot_number"] = standalone.group(1)

    # Location hints (Mouza / Upazila)
    locations = [
        "Savar", "Paba", "Sitakunda", "Keraniganj", "Hathazari", "Rupsha", "Gazipur",
        "সাভার", "পবা", "সীতাকুণ্ড", "রূপসা", "কেরানীগঞ্জ", "হাটহাজারী", "গাজীপুর"
    ]
    for loc in locations:
        if loc.lower() in text.lower():
            entities["location"] = loc
            break

    return entities


def parse_bilingual_intent(
    query_text: str,
    language_preference: Optional[str] = "auto",
    registry_lookup_fn: Optional[Any] = None,
    complaint_lookup_fn: Optional[Any] = None,
    deed_lookup_fn: Optional[Any] = None,
    current_user: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Parses natural language voice transcript or text query, returns classified intent,
    extracted legal entities, bilingual spoken readbacks, and suggested interface actions.
    Truthfully checks cadastral registry and enforces RBAC authorization on complaints.
    """
    raw_query = (query_text or "").strip()
    if not raw_query:
        return {
            "intent": "EMPTY_QUERY",
            "language": "en" if language_preference == "en" else "bn",
            "confidence": 0.0,
            "entities": {},
            "spoken_response_en": "I did not hear any input. Please speak or type your land query.",
            "spoken_response_bn": "কোনো বার্তা পাওয়া যায়নি। অনুগ্রহ করে আপনার প্রশ্নটি বলুন বা লিখুন।",
            "confirmation_required": False,
            "suggested_action": None,
        }

    # Fallback to web service resolvers if not explicitly injected
    if registry_lookup_fn is None:
        try:
            from src.landguard_web.service import service
            registry_lookup_fn = service.get_parcel_details
        except Exception:
            registry_lookup_fn = None

    if complaint_lookup_fn is None:
        try:
            from src.landguard_web.service import service
            complaint_lookup_fn = service.get_complaint
        except Exception:
            complaint_lookup_fn = None

    if deed_lookup_fn is None:
        try:
            from src.landguard_web.service import service
            deed_lookup_fn = service.lookup_deed
        except Exception:
            deed_lookup_fn = None

    # In Auto mode: bidirectional phonetic speech normalization
    if language_preference == "auto":
        normalized_english = normalize_transliterated_english(raw_query)
        if normalized_english != raw_query:
            raw_query = normalized_english
        else:
            normalized_bengali = normalize_romanized_bengali(raw_query)
            if normalized_bengali != raw_query:
                raw_query = normalized_bengali
            elif re.search(r"\b(dak|dag)\s*(?:bam\s*bahut|bam|bahut|number|no\.?|#)?\s*\d+\b", raw_query, re.IGNORECASE):
                # Spoken Bengali transcribed by English ASR e.g. 'Dak Bam bahut 307' / 'dag 9044'
                bn_norm = re.sub(
                    r"\b(?:dak|dag)\s*(?:bam\s*bahut|bam|bahut|number|no\.?|#)?\s*(\d+)\b",
                    r"দাগ নম্বর \1",
                    raw_query,
                    flags=re.IGNORECASE,
                )
                raw_query = to_bn_digits(bn_norm)

    # 0. Stop Daffodil / Hands-Free Deactivation Control (Checked first before wake word stripping)
    _stop_action_words = r"(?:stop|shut\s+down|deactivate|exit|bye|goodbye|স্টপ|বন্ধ\s*করো?|থামো)"
    stop_daffodil_patterns = [
        rf"(?:^|[^\u0980-\u09FFa-zA-Z0-9]){_stop_action_words}[\s,.:;!?-]+{_DAFFODIL_WORDS}(?:$|[^\u0980-\u09FFa-zA-Z0-9])",
        rf"(?:^|[^\u0980-\u09FFa-zA-Z0-9]){_DAFFODIL_WORDS}[\s,.:;!?-]+(?:বন্ধ|থামো|বন্ধ\s*করো?)(?:$|[^\u0980-\u09FFa-zA-Z0-9])",
        r"\b(?:turn\s+off\s+hands\s*free|disable\s+hands\s*free|হ্যান্ডস\s*ফ্রি\s*বন্ধ)\b",
    ]
    if any(re.search(pat, raw_query, re.IGNORECASE) for pat in stop_daffodil_patterns):
        det_lang = detect_language(raw_query)
        lang = det_lang if language_preference == "auto" else (language_preference or det_lang)
        return {
            "intent": "CONTROL_STOP_DAFFODIL",
            "language": lang,
            "confidence": 0.99,
            "entities": {"hands_free_deactivate": True, "wake_word_detected": True},
            "spoken_response_en": "Hands-Free mode deactivated. Assistant is standing by.",
            "spoken_response_bn": "হ্যান্ডস-ফ্রি মোড বন্ধ করা হলো।",
            "confirmation_required": False,
            "suggested_action": {
                "action": "DEACTIVATE_HANDS_FREE",
                "target": "STANDBY",
                "label": "Hands-Free OFF",
            },
        }

    # 1. Wake word detection & stripping
    wake_detected, cleaned_command = strip_wake_word(raw_query)
    entities = {}
    if wake_detected:
        entities["wake_word_detected"] = True
        if not cleaned_command:
            det_lang = detect_language(raw_query)
            lang = det_lang if language_preference == "auto" else (language_preference or det_lang)
            spoken_en = "Hello Daffodil active! I am listening for your command."
            spoken_bn = "হ্যালো ড্যাফোডিল সক্রিয় হয়েছে! আপনার কমান্ড বলুন।"
            return {
                "intent": "WAKE_WORD_ACTIVATION",
                "language": lang,
                "confidence": 0.99,
                "entities": entities,
                "spoken_response_en": spoken_en,
                "spoken_response_bn": spoken_bn,
                "confirmation_required": False,
                "suggested_action": {
                    "action": "LISTEN",
                    "target": "VOICE_COMMAND",
                    "label": "Listening for Command",
                },
            }
        else:
            raw_query = cleaned_command

    detected_lang = detect_language(raw_query)
    lang = detected_lang if language_preference == "auto" else (language_preference or detected_lang)

    norm_text = to_en_digits(raw_query).lower()
    extracted = extract_entities(raw_query)
    entities.update(extracted)

    # Authoritative registry lookup: if plot not yet identified, check if standalone 3-5 digit number matches registry
    if (
        not entities.get("dag_plot_number")
        and not entities.get("verification_id")
        and not entities.get("deed_number")
        and not entities.get("complaint_id")
    ):
        standalone_cand = re.search(r"\b([1-9]\d{2,4})\b", norm_text)
        if standalone_cand and registry_lookup_fn:
            try:
                candidate_plot = standalone_cand.group(1)
                if registry_lookup_fn(candidate_plot):
                    entities["dag_plot_number"] = candidate_plot
            except Exception:
                pass

    plot = entities.get("dag_plot_number")
    plot_bn = to_bn_digits(plot) if plot else ""
    vid = entities.get("verification_id")
    cid = entities.get("complaint_id")
    deed = entities.get("deed_number")

    # Guard: Administrative RBAC Access Restriction
    admin_patterns = [
        r"\b(?:admin\s+cases?|admin\s+docket|admin\s+audit|admin\s+reports?|admin\s+users?|admin\s+settings?|admin\s+panel|admin\s+portal|admin\s+dashboard)\b",
        r"\b(?:অ্যাডমিন\s*কেস|অ্যাডমিন\s*ডকেট|অ্যাডমিন\s*অডিট|প্রশাসনিক\s*কেস|প্রশাসনিক\s*প্যানেল)\b",
    ]
    if any(re.search(pat, raw_query, re.IGNORECASE) for pat in admin_patterns):
        user_role = str(current_user.get("role", "")).upper() if current_user else "CITIZEN"
        if user_role != "ADMIN":
            return {
                "intent": "ACCESS_RESTRICTED",
                "language": lang,
                "confidence": 0.98,
                "entities": entities,
                "spoken_response_en": "Access restricted: Administrative controls are restricted to authorized land officers and unavailable to citizens.",
                "spoken_response_bn": "অনুমতি নেই: প্রশাসনিক সেকশনে প্রবেশের অধিকার শুধুমাত্র দায়িত্বপ্রাপ্ত কর্মকর্তার রয়েছে।",
                "confirmation_required": False,
                "suggested_action": {
                    "action": "NAVIGATE",
                    "url": "/user/dashboard",
                    "target": "USER_DASHBOARD",
                    "label": "Return to Citizen Dashboard",
                },
            }

    # Navigation Command Registry: Direct Menu & Page Navigation
    # A. Verification History
    history_nav_patterns = [
        r"\b(?:open\s+verification\s+history|go\s+to\s+verification\s+history|show\s+verification\s+history|view\s+verification\s+history|verification\s+history|audit\s+history|my\s+verifications|check\s+history|view\s+history)\b",
        r"\b(?:যাচাই\s*ইতিহাস|ভেরিফিকেশন\s*ইতিহাস|পূর্ববর্তী\s*যাচাই|যাচাইয়ের\s*ইতিহাস|আগের\s*যাচাইসমূহ|ইতিহাস\s*দেখাও|হিস্ট্রি|হিস্টোরি)\b",
    ]
    if any(re.search(pat, raw_query, re.IGNORECASE) for pat in history_nav_patterns) and not vid:
        return {
            "intent": "NAVIGATE_HISTORY",
            "language": lang,
            "confidence": 0.96,
            "entities": entities,
            "spoken_response_en": "Navigating to your Verification History.",
            "spoken_response_bn": "আপনার যাচাইকরণ ইতিহাস পেজে নিয়ে যাওয়া হচ্ছে।",
            "confirmation_required": False,
            "suggested_action": {
                "action": "NAVIGATE",
                "url": "/user/history",
                "target": "VERIFICATION_HISTORY",
                "label": "View Verification History",
            },
        }

    # B. Citizen Dashboard
    dashboard_nav_patterns = [
        r"\b(?:open\s+dashboard|go\s+to\s+dashboard|show\s+dashboard|view\s+dashboard|dashboard|main\s+menu|home\s+page)\b",
        r"\b(?:ড্যাশবোর্ড|ড্যাসবোর্ড|ড্যাশবর্ড|দেশবোর্ড|ড্যাশবোর্ডে\s+যাও|হোম\s+পেজ|মূল\s+পাতা|হোমে\s+যাও)\b",
    ]
    if any(re.search(pat, raw_query, re.IGNORECASE) for pat in dashboard_nav_patterns):
        return {
            "intent": "NAVIGATE_DASHBOARD",
            "language": lang,
            "confidence": 0.96,
            "entities": entities,
            "spoken_response_en": "Opening your Citizen Dashboard.",
            "spoken_response_bn": "নাগরিক ড্যাশবোর্ড ওপেন করা হচ্ছে।",
            "confirmation_required": False,
            "suggested_action": {
                "action": "NAVIGATE",
                "url": "/user/dashboard",
                "target": "USER_DASHBOARD",
                "label": "Open Dashboard",
            },
        }

    # C. Notifications & System Alerts
    notif_nav_patterns = [
        r"\b(?:show\s+notifications?|open\s+notifications?|go\s+to\s+notifications?|view\s+notifications?|my\s+notifications?|view\s+alerts|show\s+alerts)\b",
        r"\b(?:notifications?|alerts)\b",
        r"\b(?:নোটিফিকেশন|বিজ্ঞপ্তি|সতর্কবার্তা|বার্তা\s+দেখাও|নোটিফিকেশন\s+দেখাও|বিজ্ঞপ্তি\s+দেখাও)\b",
    ]
    if any(re.search(pat, raw_query, re.IGNORECASE) for pat in notif_nav_patterns):
        return {
            "intent": "NAVIGATE_NOTIFICATIONS",
            "language": lang,
            "confidence": 0.96,
            "entities": entities,
            "spoken_response_en": "Opening your Notifications and live system alerts.",
            "spoken_response_bn": "আপনার নোটিফিকেশন ও সতর্কবার্তা পেজ ওপেন করা হচ্ছে।",
            "confirmation_required": False,
            "suggested_action": {
                "action": "NAVIGATE",
                "url": "/user/notifications",
                "target": "NOTIFICATIONS",
                "label": "View Notifications",
            },
        }

    # D. Complaints Listing (Distinct from filing or specific complaint status)
    complaints_list_patterns = [
        r"\b(?:open\s+complaints?|go\s+to\s+complaints?|show\s+complaints?|view\s+complaints?|my\s+complaints?|grievance\s+queue|dispute\s+cases?)\b",
        r"\b(?:অভিযোগসমূহ|আমার\s+অভিযোগ|অভিযোগ\s+তালিকা|অভিযোগগুলো\s+দেখাও|মামলাসমূহ)\b",
    ]
    if any(re.search(pat, raw_query, re.IGNORECASE) for pat in complaints_list_patterns) and not cid and not plot:
        return {
            "intent": "NAVIGATE_COMPLAINTS",
            "language": lang,
            "confidence": 0.96,
            "entities": entities,
            "spoken_response_en": "Navigating to your Grievance Queue.",
            "spoken_response_bn": "আপনার অভিযোগ ও বিরোধ নিষ্পত্তি তালিকায় নিয়ে যাওয়া হচ্ছে।",
            "confirmation_required": False,
            "suggested_action": {
                "action": "NAVIGATE",
                "url": "/user/complaints",
                "target": "MY_COMPLAINTS",
                "label": "View Complaints Queue",
            },
        }

    # E. Cadastral Registry (All Parcels)
    parcels_list_patterns = [
        r"\b(?:open\s+cadastral\s+registry|go\s+to\s+cadastral\s+registry|show\s+parcels?|go\s+to\s+parcels?|view\s+parcels?|land\s+registry|cadastral\s+ledger|all\s+plots?)\b",
        r"\b(?:ক্যাডাস্ট্রাল\s+রেজিস্ট্রি|পার্সেল\s+তালিকা|জমির\s+রেজিস্ট্রি|সব\s+প্লট|খতিয়ান\s+রেজিস্ট্রি)\b",
    ]
    if any(re.search(pat, raw_query, re.IGNORECASE) for pat in parcels_list_patterns) and not plot:
        return {
            "intent": "NAVIGATE_PARCELS",
            "language": lang,
            "confidence": 0.95,
            "entities": entities,
            "spoken_response_en": "Opening the Cadastral Survey Registry.",
            "spoken_response_bn": "ক্যাডাস্ট্রাল সার্ভে রেজিস্ট্রি ওপেন করা হচ্ছে।",
            "confirmation_required": False,
            "suggested_action": {
                "action": "NAVIGATE",
                "url": "/user/parcels",
                "target": "PARCEL_SEARCH",
                "label": "Search Cadastral Registry",
            },
        }

    # F. Verify Deed Portal
    verify_page_patterns = [
        r"\b(?:open\s+verification|go\s+to\s+verification|verify\s+deed|verify\s+document|verify\s+land|new\s+verification|start\s+verification)\b",
        r"\b(?:নতুন\s+যাচাই|দলিল\s+যাচাই\s+করুন|ভেরিফাই\s+পেজ|যাচাই\s+পেজ)\b",
    ]
    if any(re.search(pat, raw_query, re.IGNORECASE) for pat in verify_page_patterns) and not vid and not plot and not deed:
        return {
            "intent": "NAVIGATE_VERIFY",
            "language": lang,
            "confidence": 0.95,
            "entities": entities,
            "spoken_response_en": "Opening the Deed Verification portal.",
            "spoken_response_bn": "দলিল যাচাইকরণ পেজ ওপেন করা হচ্ছে।",
            "confirmation_required": False,
            "suggested_action": {
                "action": "NAVIGATE",
                "url": "/user/verify",
                "target": "VERIFY_DEED",
                "label": "Open Verification Portal",
            },
        }

    # G. Citizen Profile
    profile_patterns = [
        r"\b(?:open\s+profile|show\s+profile|go\s+to\s+profile|view\s+profile|my\s+profile|my\s+digital\s+id|digital\s+identity)\b",
        r"\b(?:আমার\s+প্রোফাইল|প্রোফাইল|ডিজিটাল\s+আইডি|পরিচয়পত্র|প্রোফাইলে\s+যাও)\b",
    ]
    if any(re.search(pat, raw_query, re.IGNORECASE) for pat in profile_patterns):
        return {
            "intent": "NAVIGATE_PROFILE",
            "language": lang,
            "confidence": 0.95,
            "entities": entities,
            "spoken_response_en": "Opening your Citizen Profile and Digital Identity card.",
            "spoken_response_bn": "আপনার প্রোফাইল ও ডিজিটাল পরিচিতিপত্র ওপেন করা হচ্ছে।",
            "confirmation_required": False,
            "suggested_action": {
                "action": "NAVIGATE",
                "url": "/user/profile",
                "target": "USER_PROFILE",
                "label": "View Profile",
            },
        }

    # H. Settings / Preferences
    settings_patterns = [
        r"\b(?:open\s+settings|go\s+to\s+settings|show\s+settings|preferences|system\s+settings|account\s+settings)\b",
        r"\b(?:সেটিংস|পছন্দসমূহ|সেটিংসে\s+যাও)\b",
    ]
    if any(re.search(pat, raw_query, re.IGNORECASE) for pat in settings_patterns):
        return {
            "intent": "NAVIGATE_SETTINGS",
            "language": lang,
            "confidence": 0.95,
            "entities": entities,
            "spoken_response_en": "Navigating to System Preferences and Settings.",
            "spoken_response_bn": "সিস্টেম সেটিংস ও পছন্দসমূহ পেজে নিয়ে যাওয়া হচ্ছে।",
            "confirmation_required": False,
            "suggested_action": {
                "action": "NAVIGATE",
                "url": "/user/settings",
                "target": "USER_SETTINGS",
                "label": "Open Settings",
            },
        }

    # I. Back Navigation
    back_patterns = [
        r"\b(?:go\s+back|navigate\s+back|previous\s+page)\b",
        r"\b(?:পিছনে\s+যান|আগের\s+পাতা|পেছনে\s+যাও)\b",
    ]
    if any(re.search(pat, raw_query, re.IGNORECASE) for pat in back_patterns):
        return {
            "intent": "NAVIGATE_BACK",
            "language": lang,
            "confidence": 0.95,
            "entities": entities,
            "spoken_response_en": "Returning to the previous page.",
            "spoken_response_bn": "পূর্ববর্তী পৃষ্ঠায় ফিরে যাওয়া হচ্ছে।",
            "confirmation_required": False,
            "suggested_action": {
                "action": "BACK",
                "url": "javascript:window.history.back()",
                "target": "PREVIOUS_PAGE",
                "label": "Go Back",
            },
        }

    # J0. Stop Daffodil / Hands-Free Deactivation Control
    stop_daffodil_patterns = [
        rf"(?:^|[^\u0980-\u09FFa-zA-Z0-9]){_stop_action_words}[\s,.:;!?-]+{_DAFFODIL_WORDS}(?:$|[^\u0980-\u09FFa-zA-Z0-9])",
        rf"(?:^|[^\u0980-\u09FFa-zA-Z0-9]){_DAFFODIL_WORDS}[\s,.:;!?-]+(?:বন্ধ|থামো|বন্ধ\s*করো?)(?:$|[^\u0980-\u09FFa-zA-Z0-9])",
        r"\b(?:turn\s+off\s+hands\s*free|disable\s+hands\s*free|হ্যান্ডস\s*ফ্রি\s*বন্ধ)\b",
    ]
    if any(re.search(pat, raw_query, re.IGNORECASE) for pat in stop_daffodil_patterns):
        entities["hands_free_deactivate"] = True
        return {
            "intent": "CONTROL_STOP_DAFFODIL",
            "language": lang,
            "confidence": 0.99,
            "entities": entities,
            "spoken_response_en": "Hands-Free mode deactivated. Assistant is standing by.",
            "spoken_response_bn": "হ্যান্ডস-ফ্রি মোড বন্ধ করা হলো।",
            "confirmation_required": False,
            "suggested_action": {
                "action": "DEACTIVATE_HANDS_FREE",
                "target": "STANDBY",
                "label": "Hands-Free OFF",
            },
        }

    # J. Stop / Standby Control
    stop_patterns = [
        r"\b(?:stop\s+listening|shut\s+up|standby)\b",
        r"\b(?:থামো|বাতিল|বন্ধ\s+কর)\b",
    ]
    if any(re.search(pat, raw_query, re.IGNORECASE) for pat in stop_patterns):
        return {
            "intent": "CONTROL_STOP",
            "language": lang,
            "confidence": 0.95,
            "entities": entities,
            "spoken_response_en": "Stopping speech and returning to wake-word standby.",
            "spoken_response_bn": "ভয়েস কমান্ড স্থগিত করা হলো।",
            "confirmation_required": False,
            "suggested_action": {
                "action": "STOP",
                "target": "STANDBY",
                "label": "Standby Mode",
            },
        }

    # 0. Complaint Status Query Intent (handles complaint ID lookup or status questions)
    status_keywords = ["status", "অবস্থা", "ফলাফল", "অগ্রগতি", "progress", "update", "নোট"]
    if cid or (any(k in norm_text for k in status_keywords) and any(c in norm_text for c in ["complaint", "অভিযোগ", "মামলা"])):
        target_cid = cid or "CMP-2026-001"
        comp_record = None
        if complaint_lookup_fn:
            try:
                comp_record = complaint_lookup_fn(target_cid)
            except Exception:
                comp_record = None

        if cid and complaint_lookup_fn and not comp_record:
            return {
                "intent": "COMPLAINT_NOT_FOUND",
                "language": lang,
                "confidence": 0.95,
                "entities": entities,
                "spoken_response_en": f"Complaint {target_cid} was not found in the grievance records. Please check the tracking reference.",
                "spoken_response_bn": f"অভিযোগ নম্বর {target_cid} খুঁজে পাওয়া যায়নি। অনুগ্রহ করে ট্র্যাকিং নম্বরটি পরীক্ষা করুন।",
                "confirmation_required": False,
                "suggested_action": {
                    "action": "NAVIGATE",
                    "url": "/user/complaints",
                    "target": "MY_COMPLAINTS",
                    "label": "View Grievance Queue",
                },
            }

        if comp_record and current_user:
            user_role = str(current_user.get("role", "")).upper()
            user_id = str(current_user.get("user_id", ""))
            owner_id = str(comp_record.get("citizen_user_id", ""))
            if user_role == "CITIZEN" and owner_id and user_id and owner_id != user_id:
                return {
                    "intent": "ACCESS_RESTRICTED",
                    "language": lang,
                    "confidence": 0.96,
                    "entities": entities,
                    "spoken_response_en": f"Access restricted: Complaint {target_cid} belongs to another citizen and contains protected personal information.",
                    "spoken_response_bn": f"অনুমতি নেই: অভিযোগ নম্বর {target_cid} অন্য একজন নাগরিকের অন্তর্ভুক্ত এবং সুরক্ষিত ব্যক্তিগত তথ্যযুক্ত।",
                    "confirmation_required": False,
                    "suggested_action": {
                        "action": "NAVIGATE",
                        "url": "/user/complaints",
                        "target": "MY_COMPLAINTS",
                        "label": "View My Complaints",
                    },
                }

        return {
            "intent": "COMPLAINT_STATUS",
            "language": lang,
            "confidence": 0.96,
            "entities": entities,
            "spoken_response_en": f"Found complaint {target_cid}. Investigator review timeline, expedite status, and case notes are available.",
            "spoken_response_bn": f"অভিযোগ নম্বর {target_cid} পাওয়া গেছে। তদন্তের অগ্রগতি, অগ্রাধিকারের অবস্থা ও কর্মকর্তার নোট প্রস্তুত রয়েছে।",
            "confirmation_required": False,
            "suggested_action": {
                "action": "NAVIGATE",
                "url": f"/user/complaints/{target_cid}",
                "target": "COMPLAINT_DETAIL",
                "label": "View Complaint Progress",
            },
        }

    # 1. Complaint Filing Intent
    complaint_keywords = [
        "complaint", "fraud", "double selling", "dispute", "forgery", "fake", "report", "tampered",
        "অভিযোগ", "জালিয়াতি", "ডাবল বিক্রি", "বিরোধ", "জাল দলিল", "দায়ের"
    ]
    if any(k in norm_text for k in complaint_keywords):
        if plot:
            return {
                "intent": "COMPLAINT_DRAFT",
                "language": lang,
                "confidence": 0.94,
                "entities": entities,
                "spoken_response_en": f"I have prepared a draft grievance for Plot #{plot} regarding suspected fraudulent disposition. Please review the details and confirm to submit officially.",
                "spoken_response_bn": f"দাগ নম্বর {to_bn_digits(plot)} সংক্রান্ত জালিয়াতির অভিযোগের খসড়া প্রস্তুত করা হয়েছে। দাখিলের পূর্বে বিস্তারিত তথ্য নিশ্চিত করুন।",
                "confirmation_required": True,
                "suggested_action": {
                    "action": "DRAFT_COMPLAINT",
                    "url": f"/user/complaints/new?dag={plot}&plot={plot}",
                    "label": "Confirm & Submit Grievance",
                    "preset_data": {
                        "dag_plot_number": plot,
                        "title": f"Suspected Double Disposition on Plot #{plot}",
                        "category": "SUSPECTED_DOUBLE_SALE",
                    },
                },
            }
        else:
            return {
                "intent": "COMPLAINT_DRAFT_MISSING_DETAILS",
                "language": lang,
                "confidence": 0.90,
                "entities": entities,
                "spoken_response_en": "To draft a complaint, please specify the affected Dag plot number or deed details, or proceed to the grievance portal.",
                "spoken_response_bn": "অভিযোগ দাখিলের জন্য অনুগ্রহ করে সংশ্লিষ্ট দাগ নম্বর বা দলিলের বিবরণ উল্লেখ করুন অথবা অভিযোগ ফর্মে যান।",
                "confirmation_required": False,
                "suggested_action": {
                    "action": "NAVIGATE",
                    "url": "/user/complaints/new",
                    "target": "NEW_COMPLAINT",
                    "label": "Open Complaint Form",
                },
            }

    # 2. Verification Status / Deed Query Intent
    verification_keywords = [
        "verification", "verify", "dossier", "deed status", "is my deed", "result",
        "যাচাই", "ভেরিফিকেশন", "দলিল যাচাই", "ফলাফল", "অবস্থা", "যাচাইকরণ"
    ]
    if vid:
        return {
            "intent": "VERIFICATION_STATUS",
            "language": lang,
            "confidence": 0.92,
            "entities": entities,
            "spoken_response_en": f"Found verification dossier {vid}. All deterministic statutory checks and ML risk scores are ready for inspection.",
            "spoken_response_bn": f"ভেরিফিকেশন রেকর্ড {vid} পাওয়া গেছে। সংবিধিবদ্ধ বিধিমালা ও ঝুঁকি বিশ্লেষণ ফলাফল প্রস্তুত।",
            "confirmation_required": False,
            "suggested_action": {
                "action": "NAVIGATE",
                "url": f"/verify/public/{vid}",
                "target": "VERIFICATION_DOSSIER",
                "label": "View Verification Dossier",
            },
        }
    elif deed:
        deed_record = None
        if deed_lookup_fn:
            try:
                deed_record = deed_lookup_fn(deed)
            except Exception:
                deed_record = None

        if not deed_record:
            return {
                "intent": "DEED_NOT_FOUND",
                "language": lang,
                "confidence": 0.95,
                "entities": entities,
                "spoken_response_en": f"Deed number {deed} was not found in registered records.",
                "spoken_response_bn": f"দলিল নম্বর {to_bn_digits(deed)} খুঁজে পাওয়া যায়নি।",
                "confirmation_required": False,
                "suggested_action": {
                    "action": "NAVIGATE",
                    "url": "/user/verify",
                    "target": "DEED_VERIFY",
                    "label": "Verify New Deed",
                },
            }

        # If deed is found:
        linked_vid = deed_record.get("verification_id")
        linked_plot = deed_record.get("dag_plot_number")
        if linked_vid:
            dest_url = f"/reports/{linked_vid}"
            target = "VERIFICATION_DOSSIER"
        elif linked_plot:
            dest_url = f"/user/parcels/{linked_plot}"
            target = "PARCEL_VIEW"
        else:
            dest_url = "/user/verify"
            target = "DEED_VERIFY"

        return {
            "intent": "DEED_STATUS",
            "language": lang,
            "confidence": 0.95,
            "entities": entities,
            "spoken_response_en": f"Found records for Deed #{deed}. Statutory checks and registry history are ready.",
            "spoken_response_bn": f"দলিল নম্বর {to_bn_digits(deed)} এর রেকর্ড পাওয়া গেছে। সংবিধিবদ্ধ বিধিমালা ও যাচাই ফলাফল প্রস্তুত।",
            "confirmation_required": False,
            "suggested_action": {
                "action": "NAVIGATE",
                "url": dest_url,
                "target": target,
                "label": f"View Deed #{deed}",
            },
        }
    elif any(k in norm_text for k in verification_keywords):
        return {
            "intent": "VERIFICATION_STATUS",
            "language": lang,
            "confidence": 0.88,
            "entities": entities,
            "spoken_response_en": "Please provide your Verification Dossier ID (e.g. VRF-HIST-001) or check your verification history.",
            "spoken_response_bn": "আপনার ভেরিফিকেশন ট্র্যাকিং আইডি (যেমন VRF-HIST-001) বলুন অথবা আপনার যাচাইকরণ ইতিহাসে দেখুন।",
            "confirmation_required": False,
            "suggested_action": {
                "action": "NAVIGATE",
                "url": "/user/history",
                "target": "VERIFICATION_HISTORY",
                "label": "View Verification History",
            },
        }

    # 3. Expedited Review Intent
    expedite_keywords = [
        "expedite", "urgent", "fast", "speed up", "emergency hearing", "rush",
        "জরুরি", "দ্রুত", "অগ্রাধিকার", "জরুরি শুনানি", "তাড়াতাড়ি"
    ]
    if any(k in norm_text for k in expedite_keywords):
        return {
            "intent": "EXPEDITE_QUERY",
            "language": lang,
            "confidence": 0.90,
            "entities": entities,
            "spoken_response_en": "You can request expedited hearing under Rule 14 for imminent transaction deadlines or confirmed double disposition disputes.",
            "spoken_response_bn": "আসন্ন দলিল রেজিস্ট্রি বা জরুরি বিরোধ নিষ্পত্তির জন্য বিধি ১৪ অনুযায়ী অগ্রাধিকার পর্যালোচনার আবেদন করতে পারেন।",
            "confirmation_required": False,
            "suggested_action": {
                "action": "NAVIGATE",
                "url": "/user/complaints",
                "target": "EXPEDITE_QUEUE",
                "label": "Grievance Queue",
            },
        }

    # 4. Cadastral Plot Query Intent
    plot_keywords = [
        "plot", "dag", "parcel", "holding", "khatian", "mouza",
        "দাগ", "প্লট", "খতিয়ান", "মৌজা"
    ]
    if plot:
        parcel_found = True
        if registry_lookup_fn:
            try:
                p_info = registry_lookup_fn(plot)
                parcel_found = bool(p_info)
            except Exception:
                parcel_found = False

        if not parcel_found:
            return {
                "intent": "PLOT_NOT_FOUND",
                "language": lang,
                "confidence": 0.95,
                "entities": entities,
                "spoken_response_en": f"Dag Plot #{plot} was not found in the verified cadastral survey records. Please verify the plot number or search the registry.",
                "spoken_response_bn": f"যাচাইকৃত ক্যাডাস্ট্রাল রেকর্ডে দাগ নম্বর {to_bn_digits(plot)} খুঁজে পাওয়া যায়নি। অনুগ্রহ করে দাগ নম্বরটি পরীক্ষা করুন বা রেজিস্ট্রি অনুসন্ধান করুন।",
                "confirmation_required": False,
                "suggested_action": {
                    "action": "NAVIGATE",
                    "url": "/user/parcels",
                    "target": "PARCEL_SEARCH",
                    "label": "Search Cadastral Registry",
                },
            }

        return {
            "intent": "PLOT_QUERY",
            "language": lang,
            "confidence": 0.95,
            "entities": entities,
            "spoken_response_en": f"Searching cadastral ledger for Dag Plot #{plot}. Historical survey records (CS, SA, RS, BS) and mutation status retrieved.",
            "spoken_response_bn": f"দাগ নম্বর {to_bn_digits(plot)} এর খতিয়ান ও ঐতিহাসিক রেকর্ড অনুসন্ধান করা হচ্ছে। সিএস, এসএ ও আরএস খতিয়ানের তথ্য প্রস্তুত।",
            "confirmation_required": False,
            "suggested_action": {
                "action": "NAVIGATE",
                "url": f"/user/parcels/{plot}",
                "target": "PARCEL_VIEW",
                "label": f"View Dag Plot #{plot}",
            },
        }
    elif any(k in norm_text for k in plot_keywords):
        return {
            "intent": "NEED_PLOT_NUMBER",
            "language": lang,
            "confidence": 0.90,
            "entities": entities,
            "spoken_response_en": "Please specify the Dag or Plot number you want to inspect.",
            "spoken_response_bn": "অনুগ্রহ করে আপনি যে দাগের তথ্য জানতে চান তার নম্বরটি বলুন বা লিখুন।",
            "confirmation_required": False,
            "suggested_action": {
                "action": "PROMPT_PLOT",
                "url": "/user/parcels",
                "target": "PARCEL_SEARCH",
                "label": "Search Cadastral Parcels",
            },
        }

    # 5. System Help & Instructions Check
    help_keywords = [
        "help", "how do i", "how to", "what is", "guide", "tutorial", "instructions",
        "কীভাবে", "সাহায্য", "নিয়মাবলী", "ব্যবহার নির্দেশিকা"
    ]
    if any(k in norm_text for k in help_keywords):
        return {
            "intent": "SYSTEM_HELP",
            "language": lang,
            "confidence": 0.88,
            "entities": entities,
            "spoken_response_en": "LandGuard protects your property rights by verifying deed validity, checking cadastral holding capacities, and detecting conflicting double selling. You can speak a plot number or ask to verify a deed.",
            "spoken_response_bn": "ল্যান্ডগার্ডের মাধ্যমে আপনি জমির দাগ নম্বর অনুসন্ধান, দলিলের বৈধতা যাচাই এবং দ্বৈত বিক্রির ঝুঁকি পরীক্ষা করতে পারেন। যেকোনো দাগ নম্বর বা দলিলের কথা বলুন।",
            "confirmation_required": False,
            "suggested_action": {
                "action": "NAVIGATE",
                "url": "/user/dashboard",
                "target": "HELP",
                "label": "Help & Guidance",
            },
        }

    # 5.5 Greeting / Personal Introduction Intent (e.g. "আমার নাম আশিক", "Hello", "Hi", "কেমন আছেন")
    greeting_patterns = [
        r"\b(?:hello|hi|hey|good\s+morning|good\s+afternoon|good\s+evening)\b",
        r"\b(?:আমার\s+নাম|নাম\s+আমার|স্বাগতম)\b",
        r"\b(?:my\s+name\s+is)\b",
        r"\b(?:কেমন\s+আছেন|কেমন\s+আছো|ভালোর\s+খবর|আসসালামু\s+আলাইকুম|নমস্কার)\b",
    ]
    if any(re.search(pat, raw_query, re.IGNORECASE) for pat in greeting_patterns):
        name_match = re.search(r"(?:আমার\s+নাম|my\s+name\s+is)\s+([a-zA-Z\u0980-\u09FF]+)", raw_query, re.IGNORECASE)
        citizen_name = name_match.group(1).strip() if name_match else ""
        if lang == "bn":
            spoken_bn = f"স্বাগতম {citizen_name}! ল্যান্ডগার্ড ভয়েস অ্যাসিস্ট্যান্টে আপনাকে স্বাগতম। আপনি যেকোনো দাগ নম্বর অনুসন্ধান, দলিল যাচাই বা অভিযোগের অবস্থা জানতে পারেন।" if citizen_name else "স্বাগতম! ল্যান্ডগার্ড ভয়েস অ্যাসিস্ট্যান্টে আপনাকে স্বাগতম। আপনি যেকোনো দাগ নম্বর অনুসন্ধান, দলিল যাচাই বা অভিযোগের অবস্থা জানতে পারেন।"
            spoken_en = f"Welcome {citizen_name}! Welcome to LandGuard Voice Assistant. You can inquire about any Dag plot number, verify a deed, or check complaint status." if citizen_name else "Welcome! How can LandGuard assist your land inquiry today? You can ask about a Dag plot number, verify a deed, or check complaint status."
        else:
            spoken_en = f"Hello {citizen_name}! How can LandGuard assist your land inquiry today? You can ask about a Dag plot number, verify a deed, or check complaint status." if citizen_name else "Hello! How can LandGuard assist your land inquiry today? You can ask about a Dag plot number, verify a deed, or check complaint status."
            spoken_bn = f"স্বাগতম {citizen_name}! ল্যান্ডগার্ড ভয়েস অ্যাসিস্ট্যান্টে আপনাকে স্বাগতম। আপনি যেকোনো দাগ নম্বর অনুসন্ধান, দলিল যাচাই বা অভিযোগের অবস্থা জানতে পারেন।" if citizen_name else "স্বাগতম! ল্যান্ডগার্ড ভয়েস অ্যাসিস্ট্যান্টে আপনাকে স্বাগতম। আপনি যেকোনো দাগ নম্বর অনুসন্ধান, দলিল যাচাই বা অভিযোগের অবস্থা জানতে পারেন।"
        return {
            "intent": "GREETING",
            "language": lang,
            "confidence": 0.95,
            "entities": {"citizen_name": citizen_name} if citizen_name else entities,
            "spoken_response_en": spoken_en,
            "spoken_response_bn": spoken_bn,
            "confirmation_required": False,
            "suggested_action": {
                "action": "PROMPT_PLOT",
                "url": "/user/parcels",
                "target": "PARCEL_SEARCH",
                "label": "Search Cadastral Registry",
            },
        }

    # 6. Ambiguous / Unrecognized Query Fallback (Friendly prompt to repeat or type query)
    return {
        "intent": "AMBIGUOUS_QUERY",
        "language": lang,
        "confidence": 0.35,
        "entities": entities,
        "spoken_response_en": "Could not understand, please repeat or type your search in the input box.",
        "spoken_response_bn": "বোঝা যায়নি, অনুগ্রহ করে আবার বলুন।",
        "confirmation_required": False,
        "suggested_action": {
            "action": "FOCUS_INPUT",
            "url": "#voice-text-input",
            "target": "HELP",
            "label": "Type Query Below",
        },
    }
