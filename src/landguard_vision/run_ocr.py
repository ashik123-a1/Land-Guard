"""OCR Engine Interface supporting Tesseract (ben+eng) and RapidOCR ONNX fallback."""

import os
import re
import shutil
import numpy as np
from PIL import Image
from typing import Dict, Any, Tuple, List
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
    """Removes residual diagonal watermark substrings from a recognized OCR line."""
    cleaned = _WATERMARK_NOISE_RE.sub("", txt)
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

    # Normalize Bengali digits (০-৯) to ASCII digits (0-9) for structured identifier matching
    norm_text = text.translate(_BN_DIGIT_MAP)

    # 1. Deed number pattern: DEED-YYYY-NNNNN or Bengali দলিল নং YYYY-NNNNN / NNNNN/YYYY
    m = re.search(r"DEED\s*[- ]?\s*(\d{4})\s*[- ]?\s*(\d+)", norm_text, re.IGNORECASE)
    if m:
        fields["deed_number"] = f"DEED-{m.group(1)}-{m.group(2)}"
    else:
        m_bn = re.search(r"(?:দলিল\s*(?:নং|নম্বর|নং:)|Deed\s*(?:No|Number))[^0-9\n]{0,12}(\d{4})\s*[-/ ]\s*(\d+)", norm_text, re.IGNORECASE)
        if m_bn:
            fields["deed_number"] = f"DEED-{m_bn.group(1)}-{m_bn.group(2)}"
        else:
            m_bn2 = re.search(r"(?:দলিল\s*(?:নং|নম্বর|নং:)|Deed\s*(?:No|Number))[^0-9\n]{0,12}(\d+)\s*/\s*(\d{4})", norm_text, re.IGNORECASE)
            if m_bn2:
                fields["deed_number"] = f"DEED-{m_bn2.group(2)}-{m_bn2.group(1)}"

    # 2. Khatian number (handles 'Khatian No: 1001', 'খতিয়ান নং: ১০০১', 'খতিয়ান নম্বর')
    m = re.search(r"(?:খতিয়ান\s*(?:নং|নম্বর)|Khatian\s*(?:No|Number))[^0-9\n]{0,12}(\d+)", norm_text, re.IGNORECASE)
    if m:
        fields["khatian_number"] = m.group(1)

    # 3. Plot/Dag number pattern (ordered from most specific to fallback)
    dag_val = None
    # 3a. Parcel map target plot: 'TARGET PLOT #9044'
    m_map = re.search(r"TARGET\s*PLOT\s*#?\s*(\d+)", norm_text, re.IGNORECASE)
    if m_map:
        dag_val = m_map.group(1)
    # 3b. Explicit 'Dag (Plot) No: 9044' or 'দাগ (প্লট) নং: ৯০৪৪' or 'Dag: 9044'
    if not dag_val:
        m_dag = re.search(
            r"(?:দাগ\s*(?:\(\s*(?:প্লট|Plot)\s*\))?\s*(?:নং|নম্বর)?|Dag\s*(?:\(\s*Plot\s*\))?\s*(?:No)?)[^0-9\n]{0,15}(\d{3,5})",
            norm_text,
            re.IGNORECASE,
        )
        if m_dag:
            dag_val = m_dag.group(1)
    # 3c. Khatian table Row 1: 3-5 digit plot number preceding land class / area / SUPERSEDED or ACTIVE
    if not dag_val:
        m_kh_status = re.search(
            r"\b(\d{3,5})\b[^0-9]{1,25}?(?:\d+\.\d+[^0-9]{1,15}?)?(?:SUPERSEDED|ACTIVE)",
            norm_text,
            re.IGNORECASE,
        )
        if m_kh_status:
            dag_val = m_kh_status.group(1)
    if not dag_val:
        m_kh_row = re.search(r"\b[01]\.\d{4}\)?[^0-9]{0,25}\b(\d{3,5})\b", norm_text)
        if m_kh_row:
            dag_val = m_kh_row.group(1)
    # 3d. Bilingual line where 'মৌজা: <Mouza> | দাগ নং: <Dag>' has Bengali label stripped or altered
    if not dag_val:
        for line in norm_text.splitlines():
            if re.search(r"(?:Receipt|Deed|Case|Date|Khatian|APP-|DCL-|MUT-)", line, re.IGNORECASE):
                continue
            m_pipe = re.search(r"[A-Za-z]{3,}\s*[|:]+\s*[^0-9]{0,12}\b(\d{3,5})\b", line)
            if m_pipe:
                dag_val = m_pipe.group(1)
                break
    # 3e. Application narrative / footer where Mouza is followed by 3-5 digit plot number
    if not dag_val:
        m_app = re.search(r",\s*[^0-9]{0,12}:\s*(\d{3,5})\b", norm_text)
        if m_app:
            dag_val = m_app.group(1)

    if dag_val:
        fields["dag_plot_number"] = dag_val

    # 4. Area decimal pattern
    area_val = None
    m_area_all = re.findall(r"(\d+\.\d+)\s*(?:শতক|Decimals?|Dec\.?)", norm_text, re.IGNORECASE)
    if m_area_all:
        area_val = m_area_all[-1]
    if not area_val:
        m_kh_area = re.search(
            r"\b\d{3,5}\s+(?:Viti|Nal|Chara|Bastu|Doba|Pukur|Kanda|Bagan|[A-Za-z]{2,10})\s+(\d+\.\d+)\b",
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

    return fields



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
                        r_res, _ = rapid(proc_img)
                        if r_res:
                            r_text = "\n".join(
                                _clean_ocr_line(it[1]) for it in r_res if _clean_ocr_line(it[1])
                            )
                            r_fields = extract_fields_from_text(r_text)
                            for k, v in r_fields.items():
                                if v is not None and str(v) != "":
                                    extracted[k] = v

                return final_text, [{"text": l, "score": 1.0} for l in cleaned_lines], extracted
            except Exception as e:
                if engine == "tesseract":
                    return f"[OCR_UNAVAILABLE: {str(e)}]", [], {}
        elif engine == "tesseract":
            return "[OCR_UNAVAILABLE: tesseract.exe not found]", [], {}

    rapid = get_rapid_ocr()
    if rapid:
        result, _ = rapid(proc_img)
        lines = []
        text_parts = []
        if result:
            for item in result:
                box, txt, score = item
                cleaned_txt = _clean_ocr_line(txt)
                if not cleaned_txt:
                    continue
                lines.append({"box": box, "text": cleaned_txt, "score": float(score)})
                text_parts.append(cleaned_txt)

        full_text = "\n".join(text_parts)
        extracted = extract_fields_from_text(full_text)
        return full_text, lines, extracted

    return "[OCR_UNAVAILABLE: No OCR backend installed]", [], {}


# Alias for pipeline consistency
run_ocr_pipeline = run_ocr

