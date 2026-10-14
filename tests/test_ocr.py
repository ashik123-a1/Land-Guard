"""Tests OCR text distance computation (CER, WER) and field extraction."""

from src.landguard_vision.evaluate_ocr import compute_cer, compute_wer
from src.landguard_vision.run_ocr import extract_fields_from_text


def test_cer_wer_computation():
    ref = "DEED-2023-10024"
    hyp = "DEED-2023-10024"
    assert compute_cer(ref, hyp) == 0.0
    assert compute_wer(ref, hyp) == 0.0
    
    hyp_err = "DEED-2023-10025"
    assert compute_cer(ref, hyp_err) > 0.0
    
    
def test_field_extraction():
    sample_text = "সাফ কবলা দলিল নং DEED-2023-88912 দাগ নং 4501 মোট জমি 12.50 শতক"
    extracted = extract_fields_from_text(sample_text)
    assert extracted.get("deed_number") == "DEED-2023-88912"
    assert extracted.get("dag_plot_number") == "4501"
    assert extracted.get("transferred_area_decimal") == "12.50"


def test_tabular_and_degraded_field_extraction():
    from src.landguard_vision.run_ocr import _clean_ocr_line

    raw_line = "SYNTHETIC DEMO — NOT AN OFFICIAL DOCUMENT Deed No: DEED-2024-54321"
    cleaned_line = _clean_ocr_line(raw_line)
    assert "SYNTHETIC DEMO" not in cleaned_line
    assert "DEED-2024-54321" in cleaned_line

    tabular_text = f"{cleaned_line}\n4812 Nal 18.25 ACTIVE"
    extracted = extract_fields_from_text(tabular_text)
    assert extracted.get("deed_number") == "DEED-2024-54321"
    assert extracted.get("dag_plot_number") == "4812"
    assert extracted.get("transferred_area_decimal") == "18.25"


def test_watermark_chroma_suppression_in_grayscale():
    import numpy as np
    from PIL import Image
    from src.landguard_vision.preprocess import to_grayscale

    arr = np.full((40, 40, 3), 245, dtype=np.uint8)
    # Reddish translucent watermark region: R=242, G=205, B=205 (R - G = 37 > 12)
    arr[10:20, 10:20] = [242, 205, 205]
    # Dark neutral ink stroke: R=25, G=25, B=25
    arr[25:30, 10:30] = [25, 25, 25]

    gray = to_grayscale(Image.fromarray(arr))
    # Watermark region should be suppressed to bright background (>= 240)
    assert float(gray[10:20, 10:20].mean()) >= 240.0
    # Dark ink stroke should remain dark (<= 30)
    assert float(gray[25:30, 10:30].mean()) <= 30.0


def test_ocr_date_and_nid_extraction():
    # ISO date with English prefix
    txt1 = "Deed No: DEED-2023-11223\nExecution Date: 2021-08-21\nSeller NID: SYN-1029384756"
    ext1 = extract_fields_from_text(txt1)
    assert ext1.get("execution_date") == "2021-08-21"
    assert ext1.get("seller_nid") == "SYN-1029384756"

    # Bengali prefix and numerals
    txt2 = "দলিল নং DEED-2022-99120 সম্পাদনের তারিখ: ২০২১-০৮-১৫ দাগ নং 7712"
    ext2 = extract_fields_from_text(txt2)
    assert ext2.get("execution_date") == "2021-08-15"
    assert ext2.get("dag_plot_number") == "7712"

    # Day-first format (DD-MM-YYYY)
    txt3 = "Execution Date: 15-08-2021 / (SELLER)"
    ext3 = extract_fields_from_text(txt3)
    assert ext3.get("execution_date") == "2021-08-15"

    # Multiple NIDs
    txt4 = "Party 1: SYN-1234567890 Party 2: SYN-0987654321"
    ext4 = extract_fields_from_text(txt4)
    assert ext4.get("seller_nid") == "SYN-1234567890"
    assert ext4.get("buyer_nid") == "SYN-0987654321"


def test_invalid_calendar_dates_rejected():
    """Verify that invalid calendar dates are strictly rejected rather than accepted by range-only validation."""
    # February 30th (non-existent day in all years)
    assert extract_fields_from_text("Execution Date: 2021-02-30").get("execution_date") is None

    # April 31st (April only has 30 days)
    assert extract_fields_from_text("Execution Date: 2023-04-31").get("execution_date") is None

    # February 29th on a non-leap year (2021 is not a leap year)
    assert extract_fields_from_text("Execution Date: 2021-02-29").get("execution_date") is None

    # February 29th on a valid leap year (2024 is a leap year)
    assert extract_fields_from_text("Execution Date: 2024-02-29").get("execution_date") == "2024-02-29"


def test_optical_blur_date_and_synthetic_party_ids():
    """Verify optical blur separator recovery and synthetic owner/NID party ID extraction."""
    # OCR optical blur where hyphen between year and month was dropped (e.g. 200707-20)
    blurred_date_text = "f/ Exetion Dafe: 200707-20"
    ext_blur = extract_fields_from_text(blurred_date_text)
    assert ext_blur.get("execution_date") == "2007-07-20"

    # Synthetic Owner ID format OWN-XXXXXXXX
    party_text = "Seller: OWN-ADC08EC2 Buyer: SYN-5787133150"
    ext_parties = extract_fields_from_text(party_text)
    assert ext_parties.get("seller_nid") == "OWN-ADC08EC2"
    assert ext_parties.get("buyer_nid") == "SYN-5787133150"



