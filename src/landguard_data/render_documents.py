"""Deterministic multi-template renderer for synthetic land documents with improved layout, typography, and watermarks."""

import os
from typing import Dict, Any, Tuple, List
from PIL import Image, ImageDraw, ImageFont
from .render_maps import render_parcel_map

FONT_REGULAR = "C:/Windows/Fonts/Nirmala.ttf"
FONT_BOLD = "C:/Windows/Fonts/NirmalaB.ttf"
FONT_ENG = "C:/Windows/Fonts/arial.ttf"
FONT_ENG_BOLD = "C:/Windows/Fonts/arialbd.ttf"
WATERMARK_TEXT = "SYNTHETIC DEMO — NOT AN OFFICIAL DOCUMENT"


def load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    if os.path.exists(path):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.Draw) -> List[str]:
    """Wraps text cleanly within max_width without clipping or truncation."""
    words = text.split()
    if not words:
        return [""]
    lines = []
    curr = []
    for w in words:
        test_str = " ".join(curr + [w])
        bbox = draw.textbbox((0, 0), test_str, font=font)
        if (bbox[2] - bbox[0]) <= max_width:
            curr.append(w)
        else:
            if curr:
                lines.append(" ".join(curr))
            curr = [w]
    if curr:
        lines.append(" ".join(curr))
    return lines


def apply_watermark(img: Image.Image) -> Image.Image:
    """Applies prominent, indelible diagonal synthetic watermarks across the document."""
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    
    # Create single watermark strip rotated at -28 degrees
    txt_img = Image.new("RGBA", (int(w * 1.4), 100), (255, 255, 255, 0))
    txt_draw = ImageDraw.Draw(txt_img)
    font_wm = load_font(FONT_ENG_BOLD, int(w * 0.034))
    
    # Draw double banner string
    full_str = f"{WATERMARK_TEXT}   •   {WATERMARK_TEXT}"
    txt_draw.text((20, 30), full_str, fill=(215, 35, 35, 75), font=font_wm)
    rotated = txt_img.rotate(28, expand=True, resample=Image.Resampling.BICUBIC)
    
    # Stamp rotated watermark across 3 staggered vertical bands
    rw, rh = rotated.size
    for y_offset in [int(h * 0.12), int(h * 0.45), int(h * 0.78)]:
        overlay.alpha_composite(rotated, (int(w / 2 - rw / 2), y_offset - rh // 2))
        
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def draw_fictional_seal(draw: ImageDraw.Draw, box: Tuple[int, int, int, int], text: str = "DEMO REGISTRAR SEAL"):
    x1, y1, x2, y2 = box
    draw.ellipse([x1, y1, x2, y2], outline=(30, 40, 180), width=3)
    draw.ellipse([x1 + 6, y1 + 6, x2 - 6, y2 - 6], outline=(30, 40, 180), width=1)
    font_seal = load_font(FONT_ENG_BOLD, 10)
    # Centered text
    draw.text((x1 + 12, y1 + (y2 - y1) // 2 - 8), text[:18], fill=(30, 40, 180), font=font_seal)


def draw_fictional_signature(draw: ImageDraw.Draw, x: int, y: int):
    points = [
        (x, y + 15), (x + 20, y - 5), (x + 45, y + 18),
        (x + 75, y - 8), (x + 110, y + 12), (x + 140, y)
    ]
    draw.line(points, fill=(15, 20, 60), width=2)
    draw.line([(x - 5, y + 25), (x + 150, y + 25)], fill=(150, 150, 150), width=1)


def render_sale_deed(doc: Dict[str, Any], width: int = 1000, height: int = 1400) -> Tuple[Image.Image, str, Dict[str, list], bool, bool]:
    img = Image.new("RGB", (width, height), color=(254, 252, 245))
    draw = ImageDraw.Draw(img)
    
    f_title = load_font(FONT_BOLD, 26)
    f_h2 = load_font(FONT_BOLD, 18)
    f_body = load_font(FONT_REGULAR, 15)
    f_eng_bold = load_font(FONT_ENG_BOLD, 14)
    
    bboxes = {}
    full_text = []
    
    # Page border
    draw.rectangle([35, 35, width - 35, height - 35], outline=(60, 50, 40), width=2)
    draw.rectangle([42, 42, width - 42, height - 42], outline=(150, 140, 120), width=1)
    
    # Top Revenue Stamp Box (Fictional)
    stamp_box = [width - 240, 60, width - 60, 180]
    draw.rectangle(stamp_box, outline=(180, 80, 20), width=2, fill=(255, 245, 230))
    draw.text((stamp_box[0] + 15, stamp_box[1] + 15), "DEMO STAMP", fill=(180, 80, 20), font=f_eng_bold)
    draw.text((stamp_box[0] + 15, stamp_box[1] + 45), "BDT 1,000", fill=(180, 80, 20), font=f_h2)
    draw.text((stamp_box[0] + 10, stamp_box[1] + 85), "FICTIONAL REVENUE", fill=(120, 50, 10), font=load_font(FONT_ENG, 11))
    bboxes["revenue_stamp"] = [stamp_box[1], stamp_box[0], stamp_box[3], stamp_box[2]]
    full_text.append("DEMO STAMP BDT 1,000 FICTIONAL REVENUE")
    
    # Title
    t_text = "সাফ-কবলা দলিল (DEED OF SALE)"
    draw.text((80, 75), t_text, fill=(20, 20, 20), font=f_title)
    bboxes["title"] = [75, 80, 115, 600]
    full_text.append(t_text)
    
    deed_no = f"দলিল নং / Deed No: {doc['fields']['deed_number']}"
    draw.text((80, 120), deed_no, fill=(40, 40, 40), font=f_h2)
    bboxes["deed_number"] = [120, 80, 150, 550]
    full_text.append(deed_no)
    
    exec_d = f"তারিখ / Execution Date: {doc['fields']['execution_date']}"
    draw.text((80, 155), exec_d, fill=(60, 60, 60), font=f_body)
    bboxes["execution_date"] = [155, 80, 180, 450]
    full_text.append(exec_d)
    
    # Parties Table Box
    y = 220
    draw.rectangle([65, y, width - 65, y + 260], outline=(120, 110, 100), width=1)
    draw.line([(width // 2, y), (width // 2, y + 260)], fill=(120, 110, 100), width=1)
    
    # Seller
    draw.text((85, y + 15), "১ম পক্ষ / বিক্রেতা (SELLER):", fill=(20, 20, 20), font=f_h2)
    draw.text((85, y + 55), f"নাম: {doc['fields']['seller_name_bn']}", fill=(20, 20, 20), font=f_body)
    draw.text((85, y + 85), f"Name: {doc['fields']['seller_name_en']}", fill=(40, 40, 40), font=f_body)
    draw.text((85, y + 115), f"NID: {doc['fields']['seller_nid']}", fill=(60, 60, 60), font=f_body)
    bboxes["seller"] = [y + 15, 85, y + 145, width // 2 - 20]
    full_text.extend([
        "১ম পক্ষ / বিক্রেতা (SELLER):",
        f"নাম: {doc['fields']['seller_name_bn']}",
        f"Name: {doc['fields']['seller_name_en']}",
        f"NID: {doc['fields']['seller_nid']}"
    ])
    
    # Buyer
    bx = width // 2 + 20
    draw.text((bx, y + 15), "২য় পক্ষ / ক্রেতা (BUYER):", fill=(20, 20, 20), font=f_h2)
    draw.text((bx, y + 55), f"নাম: {doc['fields']['buyer_name_bn']}", fill=(20, 20, 20), font=f_body)
    draw.text((bx, y + 85), f"Name: {doc['fields']['buyer_name_en']}", fill=(40, 40, 40), font=f_body)
    draw.text((bx, y + 115), f"NID: {doc['fields']['buyer_nid']}", fill=(60, 60, 60), font=f_body)
    bboxes["buyer"] = [y + 15, bx, y + 145, width - 85]
    full_text.extend([
        "২য় পক্ষ / ক্রেতা (BUYER):",
        f"নাম: {doc['fields']['buyer_name_bn']}",
        f"Name: {doc['fields']['buyer_name_en']}",
        f"NID: {doc['fields']['buyer_nid']}"
    ])
    
    # Property Schedule
    y = 515
    draw.text((80, y), "তপশিল সম্পত্তি (SCHEDULE OF PROPERTY):", fill=(20, 20, 20), font=f_h2)
    full_text.append("তপশিল সম্পত্তি (SCHEDULE OF PROPERTY):")
    y += 35
    draw.rectangle([65, y, width - 65, y + 330], outline=(120, 110, 100), width=1)
    
    rows = [
        f"জেলা / District: {doc['fields']['district']} | উপজেলা / Upazila: {doc['fields']['upazila']}",
        f"মৌজা / Mouza: {doc['fields']['mouza']} | জে.এল নং / JL No: {doc['fields']['jl_number']}",
        f"দাগ নং / Dag (Plot) No: {doc['fields']['dag_plot_number']}",
        f"হস্তান্তরিত জমির পরিমাণ / Transferred Area: {doc['fields']['transferred_area_decimal']} Decimal",
        f"জমির শ্রেণী / Land Class: {doc['fields']['land_classification']}",
        f"পণমূল্য / Total Consideration: BDT {doc['fields']['consideration_bdt']}",
        f"উত্তর সীমানা / North: {doc['fields']['boundary_north']} | দক্ষিণ / South: {doc['fields']['boundary_south']}"
    ]
    
    for r in rows:
        draw.text((85, y + 15), r, fill=(30, 30, 30), font=f_body)
        full_text.append(r)
        y += 44
        
    bboxes["schedule"] = [550, 85, 550 + 330, width - 85]
    
    # Sub-Registry Office
    y = 890
    s_office = f"রেজিস্ট্রি অফিস: {doc['fields']['sub_registry_office']}"
    draw.text((80, y), s_office, fill=(40, 40, 40), font=f_body)
    full_text.append(s_office)
    
    # Signatures and Seals
    y = 1040
    has_seal = doc["fields"].get("has_seal", True)
    has_sig = doc["fields"].get("has_signature", True)
    
    if has_seal:
        draw_fictional_seal(draw, (80, y, 220, y + 140), "SUB-REGISTRAR SEAL")
        bboxes["registrar_seal"] = [y, 80, y + 140, 220]
        full_text.append("SUB-REGISTRAR SEAL")
    else:
        bboxes["registrar_seal"] = [y, 80, y + 140, 220]
        
    draw.text((width - 320, y - 20), "স্বাক্ষর / Signature of Seller:", fill=(40, 40, 40), font=f_body)
    full_text.append("স্বাক্ষর / Signature of Seller:")
    bboxes["seller_signature"] = [y, width - 300, y + 50, width - 150]
    if has_sig:
        draw_fictional_signature(draw, width - 300, y + 20)
        
    img = apply_watermark(img)
    return img, "\n".join(full_text), bboxes, has_sig, has_seal


def render_khatian(doc: Dict[str, Any], width: int = 1100, height: int = 1350) -> Tuple[Image.Image, str, Dict[str, list], bool, bool]:
    """Renders high-density tabular Khatian / Porcha with multi-line wrapping and robust row layout."""
    img = Image.new("RGB", (width, height), color=(252, 252, 250))
    draw = ImageDraw.Draw(img)
    
    f_title = load_font(FONT_BOLD, 24)
    f_h2 = load_font(FONT_BOLD, 17)
    f_body = load_font(FONT_REGULAR, 14)
    f_bold = load_font(FONT_BOLD, 14)
    
    bboxes = {}
    full_text = []
    
    draw.rectangle([35, 35, width - 35, height - 35], outline=(50, 50, 50), width=2)
    
    # Header
    kh_type = doc['fields']['khatian_type']
    title = f"বাংলাদেশ ফরম নং ৫৪৬৩ (খতিয়ান — {kh_type})"
    draw.text((width // 2 - 200, 55), title, fill=(20, 20, 20), font=f_title)
    full_text.append(title)
    
    h_info = f"জেলা: {doc['fields']['district']} | উপজেলা: {doc['fields']['upazila']} | মৌজা: {doc['fields']['mouza']} | জে.এল নং: {doc['fields']['jl_number']}"
    draw.text((80, 110), h_info, fill=(30, 30, 30), font=f_h2)
    full_text.append(h_info)
    
    kh_no = f"খতিয়ান নং (Khatian No): {doc['fields']['khatian_number']} | জরিপ সন: {doc['fields']['effective_year']}"
    draw.text((80, 150), kh_no, fill=(40, 40, 40), font=f_bold)
    full_text.append(kh_no)
    
    # Khatian Table Columns: Well-balanced widths
    table_y = 210
    col_x = [60, 400, 520, 660, 810, 950, width - 60]
    headers = [
        "মালিকের নাম ও অংশ (Owner & Share)",
        "দাগ নং (Plot)",
        "শ্রেণী (Class)",
        "মোট জমি (Area)",
        "দখলকার (Possession)",
        "মন্তব্য (Remarks)"
    ]
    
    header_h = 45
    draw.rectangle([col_x[0], table_y, col_x[-1], table_y + header_h], fill=(235, 235, 230), outline=(50, 50, 50), width=1)
    for i, h in enumerate(headers):
        draw.text((col_x[i] + 8, table_y + 12), h, fill=(10, 10, 10), font=f_bold)
        full_text.append(h)
        
    # Multi-line owners formatting
    owners_raw = doc['fields']['owners_text']
    owner_lines = wrap_text(owners_raw, f_body, col_x[1] - col_x[0] - 16, draw)
    
    # Render multiple rows if available
    row_y = table_y + header_h
    row_h = max(55, len(owner_lines) * 22 + 16)
    
    # Row 1 (Primary entry)
    draw.rectangle([col_x[0], row_y, col_x[-1], row_y + row_h], outline=(80, 80, 80), width=1)
    for idx_l, line in enumerate(owner_lines):
        draw.text((col_x[0] + 10, row_y + 10 + idx_l * 20), line, fill=(20, 20, 20), font=f_body)
        
    draw.text((col_x[1] + 12, row_y + 14), doc['fields']['dag_plot_number'], fill=(20, 20, 20), font=f_body)
    draw.text((col_x[2] + 12, row_y + 14), doc['fields']['land_classification'], fill=(20, 20, 20), font=f_body)
    draw.text((col_x[3] + 12, row_y + 14), f"{doc['fields']['total_area_decimal']} শতক", fill=(20, 20, 20), font=f_body)
    draw.text((col_x[4] + 12, row_y + 14), "নিজ দখল", fill=(20, 20, 20), font=f_body)
    draw.text((col_x[5] + 12, row_y + 14), doc['fields']['status'], fill=(20, 20, 20), font=f_body)
    
    # Draw vertical gridlines
    for cx in col_x:
        draw.line([(cx, table_y), (cx, row_y + row_h + 120)], fill=(80, 80, 80), width=1)
        
    # Row 2 (Secondary ancestral plot entry for realistic page utilization)
    row2_y = row_y + row_h
    row2_dag = str(int(doc['fields']['dag_plot_number']) + 1)
    draw.rectangle([col_x[0], row2_y, col_x[-1], row2_y + 60], outline=(80, 80, 80), width=1)
    draw.text((col_x[0] + 10, row2_y + 14), "সহ-অংশীদার উত্তরাধিকারীগণ (Co-heirs)", fill=(60, 60, 60), font=f_body)
    draw.text((col_x[1] + 12, row2_y + 14), row2_dag, fill=(60, 60, 60), font=f_body)
    draw.text((col_x[2] + 12, row2_y + 14), doc['fields']['land_classification'], fill=(60, 60, 60), font=f_body)
    draw.text((col_x[3] + 12, row2_y + 14), "৫.০০ শতক", fill=(60, 60, 60), font=f_body)
    draw.text((col_x[4] + 12, row2_y + 14), "যৌথ দখল", fill=(60, 60, 60), font=f_body)
    draw.text((col_x[5] + 12, row2_y + 14), "বহাল", fill=(60, 60, 60), font=f_body)
    
    bboxes["table"] = [table_y, col_x[0], row2_y + 60, col_x[-1]]
    full_text.extend([
        owners_raw,
        doc['fields']['dag_plot_number'],
        doc['fields']['land_classification'],
        f"{doc['fields']['total_area_decimal']} শতক",
        "নিজ দখল",
        doc['fields']['status'],
        "সহ-অংশীদার উত্তরাধিকারীগণ (Co-heirs)",
        row2_dag,
        doc['fields']['land_classification'],
        "৫.০০ শতক",
        "যৌথ দখল",
        "বহাল",
        "SETTLEMENT OFFICER"
    ])
    
    # Settlement Seal
    draw_fictional_seal(draw, (80, height - 240, 220, height - 100), "SETTLEMENT OFFICER SEAL")
    bboxes["settlement_seal"] = [height - 240, 80, height - 100, 220]
    
    img = apply_watermark(img)
    return img, "\n".join(full_text), bboxes, False, True


def render_mutation_record(doc: Dict[str, Any], width: int = 1000, height: int = 1300) -> Tuple[Image.Image, str, Dict[str, list], bool, bool]:
    img = Image.new("RGB", (width, height), color=(253, 251, 246))
    draw = ImageDraw.Draw(img)
    
    f_title = load_font(FONT_BOLD, 23)
    f_h2 = load_font(FONT_BOLD, 17)
    f_body = load_font(FONT_REGULAR, 15)
    
    bboxes = {}
    full_text = []
    
    draw.rectangle([35, 35, width - 35, height - 35], outline=(50, 50, 50), width=2)
    
    title = "উপজেলা ভূমি অফিস — নামজারি ও জমাভাগ আদেশ (MUTATION ORDER)"
    draw.text((75, 65), title, fill=(20, 20, 20), font=f_title)
    full_text.append(title)
    
    case_no = f"নামজারি কেস নং / Case No: {doc['fields']['mutation_case_no']}"
    draw.text((80, 115), case_no, fill=(40, 40, 40), font=f_h2)
    bboxes["case_no"] = [115, 80, 145, 600]
    full_text.append(case_no)
    
    y = 190
    rows = [
        f"আবেদনের তারিখ / Effective Date: {doc['fields']['effective_date']}",
        f"জেলা / District: {doc['fields']['district']} | উপজেলা / Upazila: {doc['fields']['upazila']}",
        f"মৌজা / Mouza: {doc['fields']['mouza']} | দাগ নং / Dag: {doc['fields']['dag_plot_number']}",
        f"পূর্ববর্তী রেকর্ডীয় মালিক: {doc['fields']['previous_owner_bn']}",
        f"নূতন নামজারিকৃত মালিক: {doc['fields']['new_owner_bn']} ({doc['fields']['new_owner_en']})",
        f"খারিজকৃত জমির পরিমাণ: {doc['fields']['transferred_area_decimal']} Decimal",
        f"আদেশের সিদ্ধান্ত / Status: {doc['fields']['status']}"
    ]
    
    draw.rectangle([65, y, width - 65, y + 430], outline=(100, 100, 100), width=1)
    for r in rows:
        draw.text((90, y + 20), r, fill=(30, 30, 30), font=f_body)
        full_text.append(r)
        y += 58
        
    has_seal = doc["fields"].get("has_seal", True)
    has_sig = doc["fields"].get("has_signature", True)
    
    bboxes["ac_land_seal"] = [840, 80, 980, 220]
    bboxes["ac_land_sig"] = [880, width - 300, 930, width - 150]
    
    if has_seal:
        draw_fictional_seal(draw, (80, 840, 220, 980), "ASST COMMISSIONER LAND")
        full_text.append("ASST COMMISSIONER")
    if has_sig:
        draw_fictional_signature(draw, width - 300, 900)
    
    img = apply_watermark(img)
    return img, "\n".join(full_text), bboxes, has_sig, has_seal


def render_tax_receipt(doc: Dict[str, Any], width: int = 1000, height: int = 950) -> Tuple[Image.Image, str, Dict[str, list], bool, bool]:
    img = Image.new("RGB", (width, height), color=(255, 253, 245))
    draw = ImageDraw.Draw(img)
    
    f_title = load_font(FONT_BOLD, 22)
    f_body = load_font(FONT_REGULAR, 15)
    f_bold = load_font(FONT_BOLD, 15)
    
    bboxes = {}
    full_text = []
    
    draw.rectangle([35, 35, width - 35, height - 35], outline=(50, 50, 50), width=2)
    
    title = "ভূমি উন্নয়ন কর পরিশোধ দাখিলা (LAND TAX RECEIPT)"
    draw.text((width // 2 - 250, 55), title, fill=(20, 20, 20), font=f_title)
    full_text.append(title)
    
    r_no = f"দাখিলা নং / Receipt No: {doc['fields']['receipt_no']} | কর সন: {doc['fields']['tax_year']}"
    draw.text((80, 110), r_no, fill=(40, 40, 40), font=f_bold)
    bboxes["receipt_no"] = [110, 80, 140, 600]
    full_text.append(r_no)
    
    y = 175
    rows = [
        f"মালিকের নাম: {doc['fields']['owner_name_bn']}",
        f"মৌজা: {doc['fields']['mouza']} | দাগ নং: {doc['fields']['dag_plot_number']}",
        f"জমির পরিমাণ: {doc['fields']['area_decimal']} Decimal",
        f"ধার্যকৃত কর: BDT {doc['fields']['assessed_bdt']}",
        f"আদায়কৃত টাকা: BDT {doc['fields']['paid_bdt']}",
        f"পরিশোধ অবস্থা: {doc['fields']['payment_status']}"
    ]
    
    draw.rectangle([65, y, width - 65, y + 360], outline=(100, 100, 100), width=1)
    for r in rows:
        draw.text((90, y + 20), r, fill=(30, 30, 30), font=f_body)
        full_text.append(r)
        y += 54
        
    draw_fictional_seal(draw, (width - 240, 640, width - 100, 780), "UNION LAND OFFICE")
    bboxes["tax_seal"] = [640, width - 240, 780, width - 100]
    full_text.append("UNION LAND OFFICE")
    
    img = apply_watermark(img)
    return img, "\n".join(full_text), bboxes, False, True


def render_application(doc: Dict[str, Any], width: int = 1000, height: int = 1250) -> Tuple[Image.Image, str, Dict[str, list], bool, bool]:
    img = Image.new("RGB", (width, height), color=(253, 252, 248))
    draw = ImageDraw.Draw(img)
    
    f_title = load_font(FONT_BOLD, 22)
    f_h2 = load_font(FONT_BOLD, 16)
    f_body = load_font(FONT_REGULAR, 15)
    
    bboxes = {}
    full_text = []
    
    draw.rectangle([35, 35, width - 35, height - 35], outline=(50, 50, 50), width=2)
    
    title = "জমি নামজারি ও জমাখারিজের জন্য আবেদনপত্র"
    draw.text((width // 2 - 220, 55), title, fill=(20, 20, 20), font=f_title)
    full_text.append(title)
    
    app_no = f"আবেদন নং: {doc['fields']['application_no']} | তারিখ: {doc['fields']['date']}"
    draw.text((80, 110), app_no, fill=(40, 40, 40), font=f_h2)
    bboxes["app_no"] = [110, 80, 140, 550]
    full_text.append(app_no)
    
    addr_line = "বরাবর, সহকারী কমিশনার (ভূমি), " + doc['fields']['upazila']
    subj_line = f"বিষয়: {doc['fields']['subject']}"
    draw.text((80, 170), addr_line, fill=(30, 30, 30), font=f_body)
    draw.text((80, 210), subj_line, fill=(20, 20, 20), font=f_h2)
    full_text.extend([addr_line, subj_line])
    
    # Clean paragraph wrapping
    narrative = doc['fields']['narrative']
    wrapped_lines = wrap_text(narrative, f_body, width - 170, draw)
    y_narr = 270
    for l in wrapped_lines:
        draw.text((80, y_narr), l, fill=(40, 40, 40), font=f_body)
        y_narr += 30
    full_text.append(narrative)
    
    # Applicant details
    y = max(y_narr + 35, 520)
    app_name_line = f"আবেদনকারীর নাম: {doc['fields']['applicant_name_bn']}"
    app_nid_line = f"জাতীয় পরিচয়পত্র নং: {doc['fields']['applicant_nid']}"
    app_plot_line = f"মৌজা: {doc['fields']['mouza']}, দাগ নং: {doc['fields']['dag_plot_number']}"
    draw.text((80, y), app_name_line, fill=(30, 30, 30), font=f_body)
    draw.text((80, y + 35), app_nid_line, fill=(30, 30, 30), font=f_body)
    draw.text((80, y + 70), app_plot_line, fill=(30, 30, 30), font=f_body)
    full_text.extend([app_name_line, app_nid_line, app_plot_line])
    
    # Signature
    has_sig = doc["fields"].get("has_signature", True)
    draw.text((width - 320, height - 250), "আবেদনকারীর স্বাক্ষর:", fill=(40, 40, 40), font=f_body)
    full_text.append("আবেদনকারীর স্বাক্ষর:")
    bboxes["applicant_sig"] = [height - 210, width - 300, height - 160, width - 150]
    if has_sig:
        draw_fictional_signature(draw, width - 300, height - 200)
    
    img = apply_watermark(img)
    return img, "\n".join(full_text), bboxes, has_sig, False


def render_document(doc: Dict[str, Any]) -> Tuple[Image.Image, str, Dict[str, list], bool, bool]:
    dtype = doc["document_type"]
    if dtype == "SALE_DEED":
        return render_sale_deed(doc)
    elif dtype == "KHATIAN_PORCHA":
        return render_khatian(doc)
    elif dtype == "MUTATION_RECORD":
        return render_mutation_record(doc)
    elif dtype == "TAX_RECEIPT":
        return render_tax_receipt(doc)
    elif dtype == "PARCEL_MAP":
        return render_parcel_map(doc)
    elif dtype == "APPLICATION_COMPLAINT":
        return render_application(doc)
    else:
        raise ValueError(f"Unknown document_type: {dtype}")
