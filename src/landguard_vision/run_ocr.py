"""OCR Engine Interface supporting Tesseract (ben+eng) and RapidOCR ONNX fallback."""

import os
import re
import shutil
import numpy as np
from PIL import Image
from typing import Dict, Any, Tuple, List, Optional
from .preprocess import preprocess_for_ocr

# Lazy load OCR engines
_RAPID_OCR_INSTANCE = None
_TESSERACT_CMD_CACHE = None

_CANDIDATE_TESSERACT_PATHS = [
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
    r"C:\Users\ASHIK_CSE\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]


def get_tesseract_cmd() -> str:
    """Locates tesseract.exe on PATH or standard user/system installation directories."""
    global _TESSERACT_CMD_CACHE
    if _TESSERACT_CMD_CACHE is not None:
        return _TESSERACT_CMD_CACHE
    which_p = shutil.which("tesseract")
    if which_p:
        _TESSERACT_CMD_CACHE = which_p
        return _TESSERACT_CMD_CACHE
    for p in _CANDIDATE_TESSERACT_PATHS:
        if os.path.exists(p):
            _TESSERACT_CMD_CACHE = p
            return _TESSERACT_CMD_CACHE
    _TESSERACT_CMD_CACHE = ""
    return _TESSERACT_CMD_CACHE


def get_rapid_ocr():
    global _RAPID_OCR_INSTANCE
    if _RAPID_OCR_INSTANCE is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _RAPID_OCR_INSTANCE = RapidOCR()
        except ImportError:
            _RAPID_OCR_INSTANCE = False
    return _RAPID_OCR_INSTANCE


_WATERMARK_NOISE_RE = re.compile(
    r"(?:SYNTHETIC\s*DEMO|ETIC\s*DEMO|NOT\s*AN\s*OFFICIAL\s*DOCUMENT|OFFICIAL\s*DOCUMENT|FFICIAL\s*DOCUMEN)",
    re.IGNORECASE,
)

_BN_DIGIT_MAP = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

_FULL_WIDTH_PUNCT_MAP = str.maketrans({
    "\uff08": "(",
    "\uff09": ")",
    "\uff1a": ":",
    "\uff5c": "|",
    "\uff0f": "/",
    "\uff03": "#",
    "\uff0c": ",",
    "\uff0e": ".",
    "\u3010": "[",
    "\u3011": "]",
})


def _realign_unshaped_bengali_matras(text: str) -> str:
    """
    Realigns pre-base Bengali vowel signs (ি U+09BF, ে U+09C7, ৈ U+09C8) decoded from
    images rendered by Pillow without libraqm complex-script shaping (raqm=False).
    When Pillow draws logical C1 + M + C2 left-to-right without HarfBuzz reordering,
    M appears visually immediately before C2, which Tesseract decodes as C1 + C2 + M
    (or C1 + C2 + ো when C1 + ে + C2 + া is rendered).
    """
    if not text:
        return text
    # 1. C1 + C2 + \u09cb (where C1+\u09c7+C2+\u09be was drawn visually as C1 + [e][C2][a])
    s = re.sub(
        r"([\u0995-\u09b9\u09dc-\u09df])([\u0995-\u09b9\u09dc-\u09df])\u09cb",
        "\\1\u09c7\\2\u09be",
        text,
    )
    # 2. C1 + C2 + [\u09bf\u09c7\u09c8] -> C1 + [\u09bf\u09c7\u09c8] + C2
    s = re.sub(
        r"([\u0995-\u09b9\u09dc-\u09df]\u09be?)([\u0995-\u09b9\u09dc-\u09df])([\u09bf\u09c7\u09c8])",
        "\\1\\3\\2",
        s,
    )
    return s


def _clean_ocr_line(txt: str) -> str:
    """Removes residual diagonal watermark substrings and translates full-width punctuation from an OCR line."""
    cleaned = _WATERMARK_NOISE_RE.sub("", txt)
    cleaned = cleaned.translate(_FULL_WIDTH_PUNCT_MAP)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -•|")
    return cleaned.strip()


def extract_fields_from_text(text: str) -> Dict[str, str]:
    """
    Extracts structured land-record identifiers from raw OCR text.
    Note: Downstream regex extraction is measured separately from raw character/word OCR error rates.
    """
    fields: Dict[str, str] = {}
    if not text:
        return fields

    # Normalize Bengali digits (০-৯) to ASCII digits (0-9) and full-width punctuation for structured identifier matching
    norm_text = text.translate(_BN_DIGIT_MAP).translate(_FULL_WIDTH_PUNCT_MAP)

    # 1. Deed number pattern: DEED-YYYY-NNNNN or Bengali দলিল নং YYYY-NNNNN / NNNNN/YYYY
    # Handles OCR variants: DtED, (ED, [ED, Deed No, Deed Mo, Deed Ne, ছলিল নং
    m = re.search(r"\bDEED\s*[- ]?\s*(\d{4})\s*[- ]?\s*(\d+)", norm_text, re.IGNORECASE)
    if m:
        fields["deed_number"] = f"DEED-{m.group(1)}-{m.group(2)}"
    else:
        m_deed_var = re.search(
            r"(?:DEED|[\[({\<]?[DEeDt]{2,4}D|Deed\s*(?:No|Number|Mo|Nb|Ne)?:?|দলিল\s*(?:নং|নম্বর|নং:|নম্বর:)?|ছলিল\s*(?:নং|নম্বর|tt)?)[^0-9\n]{0,15}(\d{4})[-/ ]+(\d+)",
            norm_text,
            re.IGNORECASE,
        )
        if m_deed_var:
            fields["deed_number"] = f"DEED-{m_deed_var.group(1)}-{m_deed_var.group(2)}"
        else:
            m_bn = re.search(r"(?:দলিল\s*(?:নং|নম্বর|নং:)|Deed\s*(?:No|Number))[^0-9\n]{0,12}(\d{4})\s*[-/ ]\s*(\d+)", norm_text, re.IGNORECASE)
            if m_bn:
                fields["deed_number"] = f"DEED-{m_bn.group(1)}-{m_bn.group(2)}"
            else:
                m_bn2 = re.search(r"(?:দলিল\s*(?:নং|নম্বর|নং:)|Deed\s*(?:No|Number))[^0-9\n]{0,12}(\d+)\s*/\s*(\d{4})", norm_text, re.IGNORECASE)
                if m_bn2:
                    fields["deed_number"] = f"DEED-{m_bn2.group(2)}-{m_bn2.group(1)}"

    # 2. Khatian number (handles 'Khatian No: 1001', 'খতিয়ান নং: ১০০১', 'হাল খতিয়ান', 'নামজারি খতিয়ান', 'Mutated Khatian', etc.)
    m = re.search(
        r"(?:(?:হাল|সাবেক|নামজারি|নতুন|নূতন|Present|Mutated)?\s*(?:খত[িী]?[\u09df\u09af\u09bc]*া?ন|পর্চা|Khatian|Porcha)\s*(?:নং|নম্বর|নম্বরঃ|নংঃ|No|Number|#)?)[:\s\-\.=|/]*[^0-9\n]{0,12}\b(\d{1,7})\b",
        norm_text,
        re.IGNORECASE,
    )
    if m:
        fields["khatian_number"] = m.group(1)

    # 3. Plot/Dag number pattern (requires explicit field labels or cadastral table context)
    dag_val = None
    dag_provenance = "NOT_DETECTED"
    # 3a. Parcel map target plot: 'TARGET PLOT #9044' or 'TARGET DAG #5083'
    m_map = re.search(r"TARGET\s*(?:PLOT|DAG)\s*#?\s*(\d+)", norm_text, re.IGNORECASE)
    if m_map:
        dag_val = m_map.group(1)
        dag_provenance = "EXPLICIT_LABEL"
    # 3b. Explicit 'Dag (Plot) No: 9044' or 'দাগ (প্লট) নং: ৯০৪৪' or 'Dag: 9044' / 'Plot No: 6792'
    # Tolerates OCR character noise like 'লাং' for 'নং', 'Dog' for 'Dag', 'Pat' for 'Plot', and line breaks.
    # Excludes boundary plots (North/South/East/West / উত্তর/দক্ষিণ/পূর্ব/পশ্চিম / চৌহদ্দি / সীমানা).
    if not dag_val:
        dag_candidates = []
        for m_dag in re.finditer(
            r"(?:দাগ\s*(?:\(\s*(?:প্লট|Plot)\s*\))?\s*(?:নং|নম্বর|নম্বরঃ|নংঃ|লাং|নত)?|(?:[Dd][aoe]g\s*(?:\([^\)]*\)|\s*IPlo[0t]\s*|\s*Plot\s*)?|(?:\(?\s*(?:Plot|প্লট)\s*\)?))\s*(?:No|Number|#|Ma|Ne|Ns)?[:\s\-\.=|/]+)[^0-9\n]{0,15}\b(\d{1,6})\b",
            norm_text,
            re.IGNORECASE,
        ):
            start_pos = m_dag.start()
            prefix_ctx = norm_text[max(0, start_pos - 35):start_pos].lower()
            if any(b in prefix_ctx for b in ["north", "south", "east", "west", "উত্তর", "দক্ষিণ", "পূর্ব", "পশ্চিম", "চৌহদ্দি", "সীমানা", "boundary"]):
                continue
            cand = m_dag.group(1)
            # Exclude candidate if it is immediately followed by a secondary plot label keyword (e.g. in compound 'দাগ নং / 059 (Plot) No: 8210')
            post_ctx = norm_text[m_dag.end():min(len(norm_text), m_dag.end() + 25)].lower()
            if re.search(r"^\s*(?:\(?\s*(?:plot|dag|দাগ|প্লট)\s*\)?\s*(?:no|number|নং|নম্বর)?[:\s\-\.=|/]+)", post_ctx):
                continue
            dag_candidates.append(cand)
        if dag_candidates:
            dag_val = dag_candidates[0]
            dag_provenance = "EXPLICIT_LABEL"
    # 3c. Cadastral / Khatian table row: 3-5 digit plot number with land class or status
    has_cadastral_ctx = bool(
        re.search(
            r"(?:khatian|খতিয়ান|খতিয়ান|schedule|তফসিল|মৌজা|mouza|cadastr|active|superseded|nal|viti|bastu|pukur|chala)",
            norm_text,
            re.IGNORECASE,
        )
    )
    if not dag_val and has_cadastral_ctx:
        m_kh_status = re.search(
            r"\b(\d{3,5})\b[^0-9]{1,25}?(?:\d+\.\d+[^0-9]{1,15}?)?(?:SUPERSEDED|ACTIVE)",
            norm_text,
            re.IGNORECASE,
        )
        if m_kh_status:
            dag_val = m_kh_status.group(1)
            dag_provenance = "TABLE_CONTEXT"
        if not dag_val:
            m_kh_row = re.search(r"\b[01]\.\d{4}\)?[^0-9]{0,25}\b(\d{3,5})\b", norm_text)
            if m_kh_row:
                dag_val = m_kh_row.group(1)
                dag_provenance = "TABLE_CONTEXT"
        if not dag_val:
            m_kh_class = re.search(r"\b(\d{3,5})\s+(?:Viti|Nal|Chara|Bastu|Doba|Pukur|Kanda|Bagan|Chala)\b", norm_text, re.IGNORECASE)
            if m_kh_class:
                dag_val = m_kh_class.group(1)
                dag_provenance = "TABLE_CONTEXT"

    if dag_val:
        fields["dag_plot_number"] = dag_val
        fields["_dag_plot_provenance"] = dag_provenance

    # 4. Area decimal pattern (handles '8.38 Decimal', '৮.৩৮ শতক', 'Transferred Area: 8.38', 'Transtered')
    area_val = None
    m_area_labeled = re.search(
        r"(?:Transferred\s*Area|Transtered|Total\s*Area|হস্তান্তরিত\s*জমির\s*পরিমাণ|জমির\s*পরিমাণ)[^0-9\n]{0,20}(\d+\.\d+)",
        norm_text,
        re.IGNORECASE,
    )
    if m_area_labeled:
        area_val = m_area_labeled.group(1)
    if not area_val:
        m_area_all = re.findall(r"(\d+\.\d+)\s*(?:শতক|Decimals?|Dec\.?|ডেসিমেল|ডিসিমেল)", norm_text, re.IGNORECASE)
        if m_area_all:
            area_val = m_area_all[-1]
    if not area_val:
        m_kh_area = re.search(
            r"\b\d{3,5}\s+(?:Viti|Nal|Chara|Bastu|Doba|Pukur|Kanda|Bagan|Chala|[A-Za-z]{2,10})\s+(\d+\.\d+)\b",
            norm_text,
            re.IGNORECASE,
        )
        if m_kh_area:
            area_val = m_kh_area.group(1)
    if not area_val:
        m_tax_area = re.search(r":\s*(\d+\.\d+)\s*(?:Dec|D|শতক)", norm_text, re.IGNORECASE)
        if m_tax_area:
            area_val = m_tax_area.group(1)

    if area_val:
        fields["transferred_area_decimal"] = area_val
        fields["total_area_decimal"] = area_val
        fields["area_decimal"] = area_val

    # 5. Execution Date pattern (handles ISO YYYY-MM-DD, DD-MM-YYYY, DD/MM/YYYY, both English and Bengali labels)
    def _is_valid_calendar_date(yyyy: int, mm: int, dd: int) -> bool:
        if not (1900 <= yyyy <= 2035):
            return False
        try:
            import datetime
            datetime.date(yyyy, mm, dd)
            return True
        except (ValueError, OverflowError):
            return False

    date_val = None
    # Prefix-based matching with optional separator between year and month (handles blurred/dropped separator e.g. 200707-20)
    m_date_prefix = re.search(
        r"(?:Execution\s*Date|Deed\s*Date|সম্পাদনের\s*তারিখ|তারিখ|Date|Exetion\s*Dafe)[^0-9\n]{0,15}(\d{4})[-/.]?(\d{1,2})[-/.](\d{1,2})",
        norm_text,
        re.IGNORECASE,
    )
    if m_date_prefix:
        yyyy, mm, dd = int(m_date_prefix.group(1)), int(m_date_prefix.group(2)), int(m_date_prefix.group(3))
        if _is_valid_calendar_date(yyyy, mm, dd):
            date_val = f"{yyyy:04d}-{mm:02d}-{dd:02d}"

    if not date_val:
        m_date_dmy = re.search(
            r"(?:Execution\s*Date|Deed\s*Date|সম্পাদনের\s*তারিখ|তারিখ|Date)[^0-9\n]{0,15}(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})",
            norm_text,
            re.IGNORECASE,
        )
        if m_date_dmy:
            dd, mm, yyyy = int(m_date_dmy.group(1)), int(m_date_dmy.group(2)), int(m_date_dmy.group(3))
            if _is_valid_calendar_date(yyyy, mm, dd):
                date_val = f"{yyyy:04d}-{mm:02d}-{dd:02d}"

    if not date_val:
        m_iso_all = re.findall(r"\b(19\d{2}|20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})\b", norm_text)
        for cand_y, cand_m, cand_d in m_iso_all:
            cy, cm, cd = int(cand_y), int(cand_m), int(cand_d)
            if _is_valid_calendar_date(cy, cm, cd):
                date_val = f"{cy:04d}-{cm:02d}-{cd:02d}"
                break

    if date_val:
        fields["execution_date"] = date_val

    # 6. Party NID / Owner ID extraction matching synthetic dataset ID formats (SYN-XXXXXXXXXX and OWN-XXXXXXXX)
    m_nids = re.findall(r"\b(SYN-\d{10}|OWN-[A-F0-9]{8}|OWN-\d+)\b", norm_text)
    if m_nids:
        fields["seller_nid"] = m_nids[0]
        if len(m_nids) > 1:
            fields["buyer_nid"] = m_nids[1]

    # 7. Mutation case number (e.g. MUT-2017-5331/Paba or Bengali নামজারি / মিউটেশন কেস)
    m_mut = re.search(r"\b(MUT\s*[- ]?\s*\d{4}\s*[- ]?\s*\d+(?:\s*/\s*[A-Za-z\u0980-\u09FF]+)?)\b", norm_text, re.IGNORECASE)
    if m_mut:
        fields["mutation_case_no"] = m_mut.group(1).replace(" ", "")
    else:
        m_mut_bn = re.search(
            r"(?:নামজারি|মিউটেশন|জমাখারিজ|Mutation)[^A-Za-z0-9\u0980-\u09FF\n]{0,15}(MUT[-\s]?\d{4}[-\s]?\d+(?:/[A-Za-z\u0980-\u09FF]+)?|\d+[/]\d+(?:-[A-Za-z\u0980-\u09FF]+)?|\d{4}[-/]\d+)",
            norm_text,
            re.IGNORECASE,
        )
        if m_mut_bn:
            fields["mutation_case_no"] = m_mut_bn.group(1).replace(" ", "")

    # 8. Previous deed reference (e.g. DEED-2001-35323 or বায়া দলিল / পূর্ববর্তী দলিল)
    m_prev = re.search(
        r"(?:পূর্ববর্তী\s*দলিল|বায়া\s*দলিল|Previous\s*Deed|Prior\s*Deed|Preceding\s*Deed)[^A-Za-z0-9\n]{0,15}(DEED[-\s]?\d{4}[-\s]?\d+|\b\d{4}[-/]\d+\b)",
        norm_text,
        re.IGNORECASE,
    )
    if m_prev:
        cand_p = m_prev.group(1).replace(" ", "")
        if not cand_p.startswith("DEED-") and "-" in cand_p:
            cand_p = f"DEED-{cand_p}"
        fields["previous_deed_ref"] = cand_p

    # 9. Consideration amount (e.g. 955246.39 BDT or মূল্য / পণমূল্য)
    m_amt = re.search(
        r"(?:পণমূল্য|বিক্রয়মূল্য|মূল্য|Consideration|Price|Amount)[^0-9\n]{0,15}(?:BDT|Tk|টাকা)?\s*([0-9,]+(?:\.\d{2})?)",
        norm_text,
        re.IGNORECASE,
    )
    if m_amt:
        clean_amt = m_amt.group(1).replace(",", "")
        try:
            if float(clean_amt) > 100:
                fields["consideration_bdt"] = clean_amt
        except ValueError:
            pass

    # 10. Mutation Status (APPROVED / PENDING / REJECTED)
    m_stat = re.search(
        r"(?:আদেশের\s*স্থিতি|স্থিতি|Status|Mutation\s*Status)[:\s\-\.=|/]+(APPROVED|PENDING|REJECTED|মঞ্জুরকৃত|অনুমোদিত|বিচারাধীন|অনিষ্পন্ন|না-মঞ্জুর|প্রত্যাখ্যাত)",
        norm_text,
        re.IGNORECASE,
    )
    if m_stat:
        raw_stat = m_stat.group(1).upper()
        if raw_stat in ("APPROVED", "মঞ্জুরকৃত", "অনুমোদিত"):
            fields["mutation_status"] = "APPROVED"
        elif raw_stat in ("PENDING", "বিচারাধীন", "অনিষ্পন্ন"):
            fields["mutation_status"] = "PENDING"
        elif raw_stat in ("REJECTED", "না-মঞ্জুর", "প্রত্যাখ্যাত"):
            fields["mutation_status"] = "REJECTED"

    # 11. Applicant / Mutated Owner Name (supports 'নূতন নামজারিকৃত মালিক', 'নূতন নামজারক্তি মালিক', 'Applicant', 'Mutated Owner', etc.)
    m_appl = re.search(
        r"(?:(?:নূ?ত[নণ]\s*)?নামজার[^\n:]{0,15}মালিক|নামজারি\s*আবেদনকারী|আবেদনকারীর?\s*নাম|আবেদনকারী|মালিকের\s*নাম|Mutated\s*Owner|New\s*Owner|Applicant\s*(?:Name)?|Owner\s*Name)[:\s\-\.=|/]+([^\n\r]+)",
        norm_text,
        re.IGNORECASE,
    )
    if m_appl:
        raw_val = m_appl.group(1).strip()
        # If English name in parentheses is present, e.g. হাবিবর আলী (Habibur Ali), prefer the clean English name
        m_paren = re.search(r"\(([A-Za-z\s\.\-]+)\)", raw_val)
        if m_paren:
            appl_clean = m_paren.group(1).strip()
        else:
            appl_clean = re.sub(r"[\(\)]", "", raw_val).strip()
        # Filter out line noise, keywords, or status
        if len(appl_clean) >= 3 and not any(k in appl_clean.lower() for k in ["status", "decimal", "mouza", "dag", "approved", "rejected", "pending"]):
            fields["applicant_name"] = appl_clean

    # 12. Geographic & Survey Metadata (Mouza, Upazila, District, JL No, Land Class, Survey Type)
    m_mouza = re.search(r"(?:মৌজা|Mouza)[:\s\-\.=|/]+([A-Za-z\u0980-\u09FF]+)", norm_text, re.IGNORECASE)
    if m_mouza:
        fields["mouza"] = m_mouza.group(1).strip()

    m_upazila = re.search(r"(?:উপজেলা|Upazila)[:\s\-\.=|/]+([A-Za-z\u0980-\u09FF]+)", norm_text, re.IGNORECASE)
    if m_upazila:
        fields["upazila"] = m_upazila.group(1).strip()

    m_dist = re.search(r"(?:জেলা|District)[:\s\-\.=|/]+([A-Za-z\u0980-\u09FF]+)", norm_text, re.IGNORECASE)
    if m_dist:
        fields["district"] = m_dist.group(1).strip()

    m_jl = re.search(r"(?:জেএল\s*নং|JL\s*(?:No|#)?)[^0-9\n]{0,10}(\d+)", norm_text, re.IGNORECASE)
    if m_jl:
        fields["jl_number"] = m_jl.group(1).strip()

    m_class = re.search(r"(?:জমির\s*শ্রেণি|শ্রেণি|Land\s*Class)[:\s\-\.=|/]+([A-Za-z\u0980-\u09FF]+)", norm_text, re.IGNORECASE)
    if m_class:
        fields["land_classification"] = m_class.group(1).strip()

    m_survey = re.search(r"\b(CS|SA|RS|BS|সি\.?এস|এস\.?এ|আর\.?এস|বি\.?এস)\b", norm_text, re.IGNORECASE)
    if m_survey:
        fields["survey_type"] = m_survey.group(1).upper()

    # 13. Tax Receipt / Dakhila particulars
    m_dak = re.search(r"(?:দাখিলা\s*নং|হোল্ডিং\s*নং|Dakhila\s*No|Holding\s*No)[:\s\-\.=|/]+([A-Za-z0-9\-/]+)", norm_text, re.IGNORECASE)
    if m_dak:
        fields["holding_number"] = m_dak.group(1).strip()

    m_fiscal = re.search(r"(?:অর্থবছর|সাল|Fiscal\s*Year)[:\s\-\.=|/]+(\d{4}(?:[-/]\d{2,4})?)", norm_text, re.IGNORECASE)
    if m_fiscal:
        fields["fiscal_year"] = m_fiscal.group(1).strip()

    return fields


def classify_document_type(
    text: str,
    lines: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Classifies an ingested document image into LandGuard statutory document types:
      - SALE_DEED: Deed of Sale / Kabala / Gift / Conveyance (সাফ-কবলা / দানপত্র / বন্টননামা)
      - MUTATION_RECORD: Mutation & Separation Order (নামজারি ও জমাভাগ আদেশ / DCR)
      - KHATIAN_PORCHA: Cadastral Survey Record of Rights (CS/SA/RS/BS খতিয়ান ও পর্চা)
      - TAX_RECEIPT: Land Development Tax Receipt (ভূমি উন্নয়ন কর দাখিলা)
      - PARCEL_MAP: Cadastral Mouza Map (মৌজা নকশা)
      - APPLICATION_COMPLAINT: Dispute application or grievance petition
      - UNRELATED_DOCUMENT: Non-land records (menus, receipts, medical records, etc.)
      - UNCERTAIN: Ambiguous text requiring user selection or manual entry
    """
    if not text:
        return {
            "document_type": "UNCERTAIN",
            "document_type_label": "Document Type Uncertain",
            "document_type_label_bn": "দলিলের ধরন অনিশ্চিত",
            "confidence": 0.0,
            "is_uncertain": True,
        }

    norm_text = text.translate(_BN_DIGIT_MAP)
    text_lower = norm_text.lower()

    header_text = ""
    if lines and len(lines) > 0:
        header_text = " ".join(l.get("text", "") for l in lines[:6]).lower()
    else:
        header_text = "\n".join(text_lower.splitlines()[:6])

    # 1. MUTATION_RECORD check (prominent in header or case reference without sale deed clause)
    is_mutation_header = any(
        k in header_text for k in [
            "mutation order", "নামজারি ও জমাভাগ আদেশ", "নামজারি আদেশ", "মিউটেশন আদেশ",
            "জমাভাগ আদেশ", "জমাখারিজ আদেশ", "নামজারি", "মিউটেশন", "জমাভাগ", "জমাখারিজ"
        ]
    )
    has_mutation_case = "mut-" in text_lower or "নামজারি কেস" in text_lower
    has_sale_header = any(
        k in header_text for k in [
            "deed of sale", "sale deed", "সাফ-কবলা", "সাফ কবলা", "কবলা দলিল",
            "দানপত্র", "হেবা", "বণ্টননামা", "বন্টননামা", "conveyance deed"
        ]
    )

    if is_mutation_header or (has_mutation_case and not has_sale_header and ("status: approved" in text_lower or "effective date" in text_lower)):
        return {
            "document_type": "MUTATION_RECORD",
            "document_type_label": "Mutation Order (নামজারি ও জমাভাগ আদেশ)",
            "document_type_label_bn": "নামজারি ও জমাভাগ আদেশ",
            "confidence": 0.95 if is_mutation_header else 0.85,
            "is_uncertain": False,
        }

    # 2. SALE_DEED check
    if has_sale_header or any(k in text_lower for k in ["সাফ-কবলা", "সাফ কবলা", "deed of sale", "দলিল নং", "deed-", "deed no"]):
        return {
            "document_type": "SALE_DEED",
            "document_type_label": "Deed of Sale (সাফ-কবলা দলিল)",
            "document_type_label_bn": "সাফ-কবলা দলিল",
            "confidence": 0.95 if has_sale_header else 0.88,
            "is_uncertain": False,
        }

    # 3. KHATIAN_PORCHA check
    if any(k in header_text or k in text_lower for k in ["record of rights", "খতিয়ান", "খতিয়ান", "পর্চা", "porcha", "khatian no"]) and not has_sale_header:
        return {
            "document_type": "KHATIAN_PORCHA",
            "document_type_label": "Khatian / Porcha (খতিয়ান ও পর্চা)",
            "document_type_label_bn": "খতিয়ান ও পর্চা",
            "confidence": 0.88,
            "is_uncertain": False,
        }

    # 4. TAX_RECEIPT check
    if any(k in text_lower for k in ["ভূমি উন্নয়ন কর", "দাখিলা", "tax receipt", "dakhila", "খাজনা আদায়", "কর পরিশোধ"]):
        return {
            "document_type": "TAX_RECEIPT",
            "document_type_label": "Land Tax Receipt (ভূমি উন্নয়ন কর দাখিলা)",
            "document_type_label_bn": "ভূমি উন্নয়ন কর দাখিলা",
            "confidence": 0.90,
            "is_uncertain": False,
        }

    # 5. PARCEL_MAP check
    if any(k in text_lower for k in ["মৌজা নকশা", "নকশা", "cadastral map", "parcel map", "target plot", "target dag"]):
        return {
            "document_type": "PARCEL_MAP",
            "document_type_label": "Cadastral Parcel Map (মৌজা নকশা)",
            "document_type_label_bn": "মৌজা নকশা",
            "confidence": 0.90,
            "is_uncertain": False,
        }

    # 6. APPLICATION_COMPLAINT check
    if any(k in text_lower for k in ["অভিযোগ", "আবেদনপত্র", "dispute petition", "complaint", "দরখাস্ত"]):
        return {
            "document_type": "APPLICATION_COMPLAINT",
            "document_type_label": "Land Dispute Complaint / Application (আবেদন / অভিযোগ)",
            "document_type_label_bn": "আবেদন / অভিযোগ",
            "confidence": 0.85,
            "is_uncertain": False,
        }

    # 7. Check if document has recognizable land markers at all
    bn_land_keywords = [
        "দলিল", "খতিয়ান", "খতিয়ান", "পর্চা", "দাগ", "প্লট", "তফসিল", "চৌহদ্দি",
        "মৌজা", "উপজেলা", "জেএল", "সাব-রেজিস্ট্রার", "নামজারি", "মিউটেশন", "দাখিলা"
    ]
    en_land_keywords = ["deed", "khatian", "dag", "plot", "mouza", "upazila", "mutation", "schedule", "cadastral"]
    has_land_marker = any(k in text_lower for k in bn_land_keywords + en_land_keywords)

    if has_land_marker:
        return {
            "document_type": "UNCERTAIN",
            "document_type_label": "Document Type Uncertain — Select the document type or use manual entry",
            "document_type_label_bn": "দলিলের ধরন অনিশ্চিত — দলিলের ধরন নির্বাচন করুন অথবা ম্যানুয়াল এন্ট্রি ব্যবহার করুন",
            "confidence": 0.50,
            "is_uncertain": True,
        }

    return {
        "document_type": "UNRELATED_DOCUMENT",
        "document_type_label": "Unrelated Document",
        "document_type_label_bn": "অননুমোদিত অ-সম্পর্কিত দলিল",
        "confidence": 0.95,
        "is_uncertain": False,
    }



def run_ocr(
    image: Image.Image,
    preprocess: bool = True,
    engine: str = "auto",
    lang: str = "ben+eng"
) -> Tuple[str, List[Dict[str, Any]], Dict[str, str]]:
    """
    Runs document OCR and returns (full_text, line_results, extracted_fields).
    Supports configurable backend selection:
      - engine="auto": Uses pretrained Tesseract 5.4.0 ('ben+eng') for bilingual text recognition,
        augmented with RapidOCR line detection for degraded alphanumeric field recovery.
      - engine="tesseract": Uses pytesseract ('ben+eng') exclusively.
      - engine="rapidocr": Uses RapidOCR ONNX (Latin/English only) exclusively.
    """
    if preprocess:
        proc_img = preprocess_for_ocr(image)
    else:
        proc_img = np.array(image)

    if engine in ("tesseract", "auto"):
        tess_cmd = get_tesseract_cmd()
        if tess_cmd:
            try:
                import pytesseract
                pytesseract.pytesseract.tesseract_cmd = tess_cmd
                raw_text = pytesseract.image_to_string(proc_img, lang=lang, config="--psm 6")
                realigned_text = _realign_unshaped_bengali_matras(raw_text)
                cleaned_lines = [
                    _clean_ocr_line(line)
                    for line in realigned_text.splitlines()
                    if _clean_ocr_line(line)
                ]
                final_text = "\n".join(cleaned_lines)
                extracted = extract_fields_from_text(final_text)

                # In 'auto' mode, fuse structured ASCII/numeric field extraction from RapidOCR's
                # cell-level DBNet text detector (which isolates table cells in Khatian and rotated scans)
                # while preserving Tesseract's bilingual (ben+eng) full-page text transcription.
                if engine == "auto":
                    rapid = get_rapid_ocr()
                    if rapid:
                        h_o, w_o = proc_img.shape[:2]
                        max_d = max(h_o, w_o)
                        if max_d > 1200:
                            s_f = 1200.0 / max_d
                            r_in = cv2.resize(proc_img, (int(w_o * s_f), int(h_o * s_f)), interpolation=cv2.INTER_AREA)
                        else:
                            r_in = proc_img
                        r_res, _ = rapid(r_in)
                        if r_res:
                            r_text = "\n".join(
                                _clean_ocr_line(it[1]) for it in r_res if _clean_ocr_line(it[1])
                            )
                            r_fields = extract_fields_from_text(r_text)
                            for k, v in r_fields.items():
                                if v is not None and str(v) != "":
                                    if k == "dag_plot_number":
                                        tess_dag = extracted.get("dag_plot_number")
                                        tess_prov = extracted.get("_dag_plot_provenance")
                                        rapid_dag = v
                                        rapid_prov = r_fields.get("_dag_plot_provenance")
                                        # Never overwrite an EXPLICIT_LABEL from Tesseract with an unanchored/table RapidOCR guess
                                        if tess_prov == "EXPLICIT_LABEL" and rapid_prov != "EXPLICIT_LABEL":
                                            continue
                                        # When RapidOCR has an EXPLICIT_LABEL or Tesseract lacks one, use RapidOCR's high-fidelity reading
                                        extracted["dag_plot_number"] = rapid_dag
                                        extracted["_dag_plot_provenance"] = rapid_prov
                                        continue
                                    extracted[k] = v

                return final_text, [{"text": l, "score": 1.0} for l in cleaned_lines], extracted
            except Exception as e:
                if engine == "tesseract":
                    return f"[OCR_UNAVAILABLE: {str(e)}]", [], {}
        elif engine == "tesseract":
            return "[OCR_UNAVAILABLE: tesseract.exe not found]", [], {}

    rapid = get_rapid_ocr()
    if rapid:
        h_orig, w_orig = proc_img.shape[:2]
        max_dim = max(h_orig, w_orig)
        if max_dim > 1200:
            scale_factor = 1200.0 / max_dim
            rapid_input = cv2.resize(
                proc_img,
                (int(w_orig * scale_factor), int(h_orig * scale_factor)),
                interpolation=cv2.INTER_AREA,
            )
        else:
            scale_factor = 1.0
            rapid_input = proc_img

        result, _ = rapid(rapid_input)
        lines = []
        text_parts = []
        if result:
            for item in result:
                box, txt, score = item
                cleaned_txt = _clean_ocr_line(txt)
                if not cleaned_txt:
                    continue
                if scale_factor != 1.0 and box is not None:
                    scaled_box = [[float(pt[0]) / scale_factor, float(pt[1]) / scale_factor] for pt in box]
                else:
                    scaled_box = box
                lines.append({"box": scaled_box, "text": cleaned_txt, "score": float(score)})
                text_parts.append(cleaned_txt)

        full_text = "\n".join(text_parts)
        extracted = extract_fields_from_text(full_text)
        return full_text, lines, extracted

    return "[OCR_UNAVAILABLE: No OCR backend installed]", [], {}


# Alias for pipeline consistency
run_ocr_pipeline = run_ocr

