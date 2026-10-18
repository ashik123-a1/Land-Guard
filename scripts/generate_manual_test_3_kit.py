"""Master generator for LandGuard Manual Test 3 kit.
Generates:
1. text_data/ structured test files (JSON, CSV, README.md)
2. samples/SAMPLE_INDEX.md
3. Core Markdown test documents in MANUAL_TEST_3/
4. Printable PDF documents matching each Markdown file
5. Official reference PDF verification certificates in PDF_REFERENCE_OUTPUTS/
"""

import os
import sys
import json
import csv
import datetime
import hashlib
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("scripts"))

from scripts.md_to_pdf import md_to_pdf
from src.landguard_web.service import LandGuardVerificationService
from src.landguard_reports.pdf_generator import generate_verification_pdf

BASE_DIR = r"F:\ashik test data\MANUAL_TEST_3"
SAMPLES_DIR = os.path.join(BASE_DIR, "samples")
TEXT_DATA_DIR = os.path.join(BASE_DIR, "text_data")
PDF_REF_DIR = os.path.join(BASE_DIR, "PDF_REFERENCE_OUTPUTS")


def generate_text_data():
    """Generates structured test inputs in JSON and CSV formats."""
    os.makedirs(TEXT_DATA_DIR, exist_ok=True)

    # 1. Ground truth payloads
    ground_truth = {
        "TC-01": {
            "test_id": "TC-01",
            "title": "Clean Deed of Sale Baseline",
            "document_type": "DEED_OF_SALE",
            "deed_number": "DEED-2001-35323",
            "dag_plot_number": "9044",
            "transferred_area_decimal": 9.24,
            "execution_date": "2001-03-15",
            "seller_nid": "SYN-1671902294",
            "buyer_nid": "SYN-4713493618",
            "mouza": "Fatehabad",
            "upazila": "Hathazari",
            "district": "Chattogram",
            "expected_outcome": "CONFIRMED_INCONSISTENCY",
            "p3_requirement": "Baseline Statutory Chain Verification",
            "evidence_type": "A (Pure OCR) / B (Human-Reviewed)",
        },
        "TC-02": {
            "test_id": "TC-02",
            "title": "Mutation Order Clean Approval Baseline",
            "document_type": "MUTATION_RECORD",
            "mutation_case_no": "MUT-2001-9502/Rupsha",
            "dag_plot_number": "9044",
            "transferred_area_decimal": 9.24,
            "mutation_status": "APPROVED",
            "effective_date": "2001-05-10",
            "mouza": "Fatehabad",
            "expected_outcome": "CLEAR_FOR_STANDARD_PROCESSING",
            "p3_requirement": "Req 4: Registration vs Mutation Consistency",
            "evidence_type": "A (Pure OCR) / B (Human-Reviewed)",
        },
        "TC-03": {
            "test_id": "TC-03",
            "title": "Cadastral Survey / Khatian Porcha Ingestion",
            "document_type": "KHATIAN_PORCHA",
            "khatian_number": "KH-358",
            "dag_plot_number": "358",
            "transferred_area_decimal": 78.84,
            "survey_type": "RS",
            "mouza": "Fatehabad",
            "expected_outcome": "CLEAR_FOR_STANDARD_PROCESSING",
            "p3_requirement": "Cadastral Record Verification",
            "evidence_type": "A (Pure OCR) / B (Human-Reviewed)",
        },
        "TC-04": {
            "test_id": "TC-04",
            "title": "Double-Selling Detection on Plot 8210 (TC-04 Fixed)",
            "document_type": "DEED_OF_SALE",
            "deed_number": "DEED-2005-23539",
            "dag_plot_number": "8210",
            "transferred_area_decimal": 31.82,
            "execution_date": "2005-07-22",
            "seller_nid": "SYN-4713493618",
            "buyer_nid": "SYN-1671902294",
            "mouza": "Fatehabad",
            "upazila": "Hathazari",
            "district": "Chattogram",
            "expected_outcome": "CONFIRMED_INCONSISTENCY",
            "expected_rules": ["RULE_AREA_EXCEEDS_CAPACITY", "RULE_SELLER_NOT_TITLEHOLDER"],
            "expected_ml_risk": "> 0.95 (High Risk / Fraud Alert)",
            "p3_requirement": "Req 2: Double-Selling / Conflicting Disposition",
            "evidence_type": "A (Pure OCR) / B (Human-Reviewed)",
        },
        "TC-05": {
            "test_id": "TC-05",
            "title": "Double-Selling Scenario: Conflicting Disposition on Plot 5083",
            "document_type": "DEED_OF_SALE",
            "deed_number": "DEED-2023-88912",
            "dag_plot_number": "5083",
            "transferred_area_decimal": 12.50,
            "seller_nid": "SYN-4713493618",
            "buyer_nid": "SYN-9988776655",
            "mouza": "Fatehabad",
            "execution_date": "2023-08-14",
            "expected_outcome": "CONFIRMED_INCONSISTENCY",
            "expected_rules": ["RULE_CONFLICTING_DOUBLE_DISPOSITION", "RULE_SELLER_NOT_TITLEHOLDER"],
            "p3_requirement": "Req 2: Double-Selling (Same Plot Sold Twice)",
            "evidence_type": "C (Demo Preset) / D (Direct Manual Entry)",
        },
        "TC-06": {
            "test_id": "TC-06",
            "title": "Altered / Tampered Deed: Text Paste-Over Anomaly",
            "document_type": "DEED_OF_SALE",
            "deed_number": "DEED-2021-65260",
            "dag_plot_number": "5235",
            "transferred_area_decimal": 15.00,
            "visual_tampering_flag": True,
            "expected_outcome": "CONFIRMED_INCONSISTENCY",
            "expected_rules": ["RULE_VISUAL_TAMPERING_DETECTED"],
            "p3_requirement": "Req 1: Forged or Altered Document Detection",
            "evidence_type": "A (Pure OCR / Vision Anomaly Engine)",
        },
        "TC-07": {
            "test_id": "TC-07",
            "title": "Forged Stamp / Mandatory Official Seal Missing",
            "document_type": "DEED_OF_SALE",
            "deed_number": "DEED-2018-91244",
            "dag_plot_number": "5083",
            "transferred_area_decimal": 8.00,
            "missing_seal_flag": True,
            "expected_outcome": "CONFIRMED_INCONSISTENCY",
            "expected_rules": ["RULE_MANDATORY_SEAL_MISSING"],
            "p3_requirement": "Req 1: Forged or Altered Document Detection",
            "evidence_type": "A (Pure OCR) / B (Human-Reviewed)",
        },
        "TC-08": {
            "test_id": "TC-08",
            "title": "Suspicious Rapid Transfer Velocity Sequence (3 Transfers in 42 Days)",
            "document_type": "DEED_OF_SALE",
            "deed_number": "DEED-2023-0142",
            "dag_plot_number": "5083",
            "transferred_area_decimal": 10.00,
            "execution_date": "2023-03-15",
            "seller_nid": "SYN-3322114455",
            "buyer_nid": "SYN-6677889900",
            "mouza": "Fatehabad",
            "expected_outcome": "CONFIRMED_INCONSISTENCY",
            "expected_rules": ["RULE_RAPID_TRANSFER_VELOCITY"],
            "p3_requirement": "Req 3: Suspicious Rapid Transfer Sequences",
            "evidence_type": "C (Demo Preset) / D (Direct Manual Entry)",
        },
        "TC-09": {
            "test_id": "TC-09",
            "title": "Suspicious Price Inflation Escalation (300% in 60 Days)",
            "document_type": "DEED_OF_SALE",
            "deed_number": "DEED-2023-0988",
            "dag_plot_number": "7873",
            "transferred_area_decimal": 8.00,
            "consideration_bdt": 4800000.0,
            "previous_consideration_bdt": 1200000.0,
            "expected_outcome": "CONFIRMED_INCONSISTENCY",
            "expected_rules": ["RULE_SUSPICIOUS_PRICE_INFLATION"],
            "p3_requirement": "Req 3: Rapid Transfer Sequences / Price Escalation",
            "evidence_type": "C (Demo Preset) / D (Direct Manual Entry)",
        },
        "TC-10": {
            "test_id": "TC-10",
            "title": "Registration vs Mutation Mismatch: Unapproved/Pending Order",
            "document_type": "MUTATION_RECORD",
            "mutation_case_no": "MUT-2006-5364/Rupsha",
            "dag_plot_number": "7873",
            "transferred_area_decimal": 81.95,
            "mutation_status": "PENDING",
            "expected_outcome": "CONFIRMED_INCONSISTENCY",
            "expected_rules": ["RULE_UNVERIFIED_MUTATION_RECORD"],
            "p3_requirement": "Req 4: Registration vs Mutation Mismatches",
            "evidence_type": "A (Pure OCR) / B (Human-Reviewed)",
        },
        "TC-11": {
            "test_id": "TC-11",
            "title": "Registration vs Mutation Mismatch: Applicant Name Contradiction",
            "document_type": "MUTATION_RECORD",
            "mutation_case_no": "MUT-2007-1130/Keraniganj",
            "dag_plot_number": "2438",
            "transferred_area_decimal": 59.95,
            "applicant_name": "Habibur Ali",
            "mutation_status": "APPROVED",
            "expected_outcome": "CLEAR_FOR_STANDARD_PROCESSING",
            "p3_requirement": "Req 4: Registration vs Mutation Verification",
            "evidence_type": "A (Pure OCR) / B (Human-Reviewed)",
        },
        "TC-12": {
            "test_id": "TC-12",
            "title": "Mutation Auto-Fill Real Image Verification with Full Provenance",
            "document_type": "MUTATION_RECORD",
            "mutation_case_no": "MUT-2002-9083/Keraniganj",
            "dag_plot_number": "4603",
            "transferred_area_decimal": 18.62,
            "expected_outcome": "CLEAR_FOR_STANDARD_PROCESSING",
            "p3_requirement": "Req 4: Mutation Record Ingestion & Field Extraction",
            "evidence_type": "A (Pure OCR) / B (Human-Reviewed)",
        },
        "TC-13": {
            "test_id": "TC-13",
            "title": "Statutory Area Excess Contradiction: 69.64 dec on 29.66 dec Capacity",
            "document_type": "DEED_OF_SALE",
            "deed_number": "DEED-2011-41265",
            "dag_plot_number": "4099",
            "transferred_area_decimal": 69.64,
            "execution_date": "2011-05-18",
            "seller_nid": "SYN-4713493618",
            "buyer_nid": "SYN-1671902294",
            "mouza": "Fatehabad",
            "expected_outcome": "CONFIRMED_INCONSISTENCY",
            "expected_rules": ["RULE_AREA_EXCEEDS_CAPACITY", "RULE_SELLER_NOT_TITLEHOLDER"],
            "expected_ml_risk": "> 0.95 (High Risk)",
            "p3_requirement": "Statutory Capacity Contradiction / Chain Defect",
            "evidence_type": "A (Pure OCR) / B (Human-Reviewed)",
        },
        "TC-14": {
            "test_id": "TC-14",
            "title": "Statutory Area Excess Contradiction: 203.89 dec on Plot 675",
            "document_type": "DEED_OF_SALE",
            "deed_number": "DEED-2012-85693",
            "dag_plot_number": "675",
            "transferred_area_decimal": 203.89,
            "expected_outcome": "CONFIRMED_INCONSISTENCY",
            "expected_rules": ["RULE_AREA_EXCEEDS_CAPACITY"],
            "p3_requirement": "Statutory Capacity Contradiction",
            "evidence_type": "A (Pure OCR) / B (Human-Reviewed)",
        },
        "TC-15": {
            "test_id": "TC-15",
            "title": "Land Development Tax Receipt (Dakhila) Ingestion",
            "document_type": "TAX_RECEIPT",
            "dag_plot_number": "7873",
            "transferred_area_decimal": 8.38,
            "fiscal_year": "1429-1430",
            "expected_outcome": "CLEAR_FOR_STANDARD_PROCESSING",
            "p3_requirement": "Tax Record Validation & Cross-Check",
            "evidence_type": "A (Pure OCR) / B (Human-Reviewed)",
        },
        "TC-16": {
            "test_id": "TC-16",
            "title": "Cadastral Mouza Map: Target Dag Identification vs Boundary",
            "document_type": "PARCEL_MAP",
            "dag_plot_number": "969",
            "expected_outcome": "CLEAR_FOR_STANDARD_PROCESSING",
            "p3_requirement": "Cadastral Survey Map Ground Truth",
            "evidence_type": "A (Pure OCR) / B (Human-Reviewed)",
        },
        "TC-17": {
            "test_id": "TC-17",
            "title": "CyberScan Gatekeeper Rejection: Restaurant Menu",
            "document_type": "UNRELATED_DOCUMENT",
            "filename": "restaurant_menu.png",
            "expected_outcome": "REJECTED_AT_INGESTION (HTTP 422)",
            "expected_error": "Document Not Recognized as a Land Record",
            "p3_requirement": "Data Integrity & Non-Land Rejection",
            "evidence_type": "A (Pure OCR Gatekeeper)",
        },
        "TC-18": {
            "test_id": "TC-18",
            "title": "CyberScan Gatekeeper Rejection: Retail POS Invoice",
            "document_type": "UNRELATED_DOCUMENT",
            "filename": "retail_invoice.png",
            "expected_outcome": "REJECTED_AT_INGESTION (HTTP 422)",
            "expected_error": "Document Not Recognized as a Land Record",
            "p3_requirement": "Data Integrity & Non-Land Rejection",
            "evidence_type": "A (Pure OCR Gatekeeper)",
        },
        "TC-19": {
            "test_id": "TC-19",
            "title": "Historical Archive: Pre-1972 Record Missing Evidence Handling",
            "document_type": "SALE_DEED",
            "deed_number": "DEED-2022-13567",
            "dag_plot_number": "3732",
            "transferred_area_decimal": 9.14,
            "expected_outcome": "MISSING_EVIDENCE",
            "p3_requirement": "Historical Archive & Honest Uncertainty",
            "evidence_type": "A (Pure OCR) / B (Human-Reviewed)",
        },
        "TC-20": {
            "test_id": "TC-20",
            "title": "Unindexed Rural Cadastral Plot: Honest Missing Evidence Routing",
            "document_type": "SALE_DEED",
            "deed_number": "DEED-2005-20185",
            "dag_plot_number": "9044",
            "transferred_area_decimal": 87.25,
            "expected_outcome": "MISSING_EVIDENCE",
            "p3_requirement": "Honest Missing Evidence vs False Accusation",
            "evidence_type": "A (Pure OCR) / B (Human-Reviewed)",
        },
        "TC-21": {
            "test_id": "TC-21",
            "title": "Boundary Plot Disambiguation (North/South Plots Excluded)",
            "document_type": "TAX_RECEIPT",
            "dag_plot_number": "9044",
            "transferred_area_decimal": 9.24,
            "expected_outcome": "CLEAR_FOR_STANDARD_PROCESSING",
            "p3_requirement": "Spatial Boundary Disambiguation",
            "evidence_type": "A (Pure OCR) / B (Human-Reviewed)",
        },
        "TC-22": {
            "test_id": "TC-22",
            "title": "Manual Direct Statutory Verification (No Upload, Direct Form Entry)",
            "document_type": "DEED_OF_SALE",
            "deed_number": "DEED-2023-DIRECT-01",
            "dag_plot_number": "5083",
            "transferred_area_decimal": 5.00,
            "seller_nid": "SYN-1671902294",
            "buyer_nid": "SYN-4713493618",
            "mouza": "Fatehabad",
            "expected_outcome": "CLEAR_FOR_STANDARD_PROCESSING",
            "p3_requirement": "Direct Form Entry & Public Service",
            "evidence_type": "D (Direct Manual Entry)",
        },
        "TC-23": {
            "test_id": "TC-23",
            "title": "Bengali Citizen Voice Assistant: Query Plot Status & Land Class",
            "voice_query_bn": "দাগ নং ৫০৮৩ এর মালিকানা স্থিতি কি?",
            "voice_query_en": "What is the ownership status of Plot 5083?",
            "target_plot": "5083",
            "expected_intent": "PLOT_STATUS_QUERY",
            "expected_response_contains": ["৫০৮৩", "Fatehabad"],
            "p3_requirement": "Citizen Accessibility & Voice Query",
            "evidence_type": "D (Citizen Voice Assistant)",
        },
        "TC-24": {
            "test_id": "TC-24",
            "title": "Verification Dossier Detail: Officer Determination & Audit Logging",
            "workflow_step": "Human Officer Review & Determination Recording",
            "determination": "REJECT_SUSPECTED_FRAUD",
            "justification": "Contradictory ownership chain confirmed against sub-registry index.",
            "expected_outcome": "AUDIT_EVENT_PERSISTED_IN_SQLITE",
            "p3_requirement": "Evidence Act Human Determination & Audit Trail",
            "evidence_type": "B (Human Officer Audit Record)",
        },
        "TC-25": {
            "test_id": "TC-25",
            "title": "Printable Statutory Audit Certificate & Reference Dossier Generation",
            "workflow_step": "PDF Report Generation with QR Code and SHA-256 Signature",
            "expected_outcome": "TAMPER_EVIDENT_PDF_GENERATED",
            "required_disclaimer": "SYNTHETIC DEMO — NOT AN OFFICIAL DOCUMENT",
            "p3_requirement": "Tamper-Evident Reporting & Legal Disclaimers",
            "evidence_type": "E (Reference Generated Output)",
        },
    }

    with open(os.path.join(TEXT_DATA_DIR, "ground_truth_payloads.json"), "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2, ensure_ascii=False)

    # 2. Chronological transfer chains
    chains = {
        "plot_5083_legitimate_chain": [
            {
                "step": 1,
                "date": "1995-02-10",
                "event": "CS/SA Cadastral Recording",
                "owner": "SYN-1671902294 (Rafiqul Islam)",
                "area_dec": 25.50,
                "document_ref": "KH-5083-CS",
            },
            {
                "step": 2,
                "date": "2005-06-18",
                "event": "Conveyance Deed of Sale",
                "seller": "SYN-1671902294",
                "buyer": "SYN-4713493618 (Nazmul Hossain)",
                "area_dec": 10.00,
                "document_ref": "DEED-2005-11029",
            },
            {
                "step": 3,
                "date": "2005-09-22",
                "event": "Mutation & Separation Order",
                "mutated_owner": "SYN-4713493618",
                "area_dec": 10.00,
                "status": "APPROVED",
                "document_ref": "MUT-2005-4421/Fatehabad",
            },
        ],
        "plot_5083_conflicting_disposition_fraud": [
            {
                "step": 4,
                "date": "2023-08-14",
                "event": "Fraudulent Second Sale by Prior Owner",
                "seller": "SYN-1671902294 (Prior Owner whose title was extinguished in 2005)",
                "buyer": "SYN-9988776655 (Third Party Victim)",
                "area_dec": 12.50,
                "document_ref": "DEED-2023-88912",
                "violation": "RULE_CONFLICTING_DOUBLE_DISPOSITION & RULE_SELLER_NOT_TITLEHOLDER",
            }
        ],
        "plot_8210_double_selling_sequence": [
            {
                "step": 1,
                "date": "1998-04-12",
                "event": "Primary Cadastral Recording",
                "owner": "SYN-1671902294",
                "capacity_dec": 19.84,
                "mouza": "Fatehabad",
            },
            {
                "step": 2,
                "date": "2005-07-22",
                "event": "Conflicting Conveyance Deed",
                "seller": "SYN-4713493618",
                "buyer": "SYN-1671902294",
                "claimed_area_dec": 31.82,
                "document_ref": "DEED-2005-23539",
                "violation": "Claims 31.82 dec on 19.84 dec parcel (Area Excess) and seller is not titleholder",
            },
        ],
    }
    with open(os.path.join(TEXT_DATA_DIR, "chronological_transfer_chains.json"), "w", encoding="utf-8") as f:
        json.dump(chains, f, indent=2, ensure_ascii=False)

    # 3. Double-selling conflict pairs
    double_sale_pairs = [
        {
            "conflict_id": "DS-01",
            "plot_number": "8210",
            "mouza": "Fatehabad",
            "legitimate_transfer": {
                "deed_number": "DEED-1998-11204",
                "execution_date": "1998-04-12",
                "seller": "SYN-9988112233",
                "buyer": "SYN-1671902294",
                "area_dec": 19.84,
                "status": "RECORDED",
            },
            "conflicting_transfer": {
                "deed_number": "DEED-2005-23539",
                "execution_date": "2005-07-22",
                "seller": "SYN-4713493618",
                "buyer": "SYN-1671902294",
                "area_dec": 31.82,
                "status": "CONFIRMED_INCONSISTENCY",
                "contradiction_type": "EXCEEDS_CAPACITY_AND_EXTINGUISHED_TITLE",
            },
        },
        {
            "conflict_id": "DS-02",
            "plot_number": "5083",
            "mouza": "Fatehabad",
            "legitimate_transfer": {
                "deed_number": "DEED-2005-11029",
                "execution_date": "2005-06-18",
                "seller": "SYN-1671902294",
                "buyer": "SYN-4713493618",
                "area_dec": 10.00,
                "status": "MUTATED_AND_RECORDED",
            },
            "conflicting_transfer": {
                "deed_number": "DEED-2023-88912",
                "execution_date": "2023-08-14",
                "seller": "SYN-1671902294",
                "buyer": "SYN-9988776655",
                "area_dec": 12.50,
                "status": "CONFIRMED_INCONSISTENCY",
                "contradiction_type": "SECOND_SALE_AFTER_COMPLETE_DISPOSITION",
            },
        },
    ]
    with open(os.path.join(TEXT_DATA_DIR, "double_selling_conflict_pairs.json"), "w", encoding="utf-8") as f:
        json.dump(double_sale_pairs, f, indent=2, ensure_ascii=False)

    # 4. Registration vs mutation mismatch pairs
    mismatch_pairs = [
        {
            "mismatch_id": "MM-01",
            "plot_number": "7873",
            "mouza": "Rupsha",
            "registration_record": {
                "deed_number": "DEED-2006-18946",
                "transferred_area_decimal": 81.95,
                "seller_nid": "SYN-7711223344",
                "buyer_nid": "SYN-5544332211",
                "status": "REGISTERED",
            },
            "mutation_record": {
                "mutation_case_no": "MUT-2006-5364/Rupsha",
                "status": "PENDING",
                "statutory_violation": "RULE_UNVERIFIED_MUTATION_RECORD",
                "risk_impact": "Transfer not mutated in land records, vendor lacks updated record of rights.",
            },
        },
        {
            "mismatch_id": "MM-02",
            "plot_number": "2438",
            "mouza": "Keraniganj",
            "registration_record": {
                "deed_number": "DEED-2007-44912",
                "transferred_area_decimal": 59.95,
                "seller_nid": "SYN-8877665544",
            },
            "mutation_record": {
                "mutation_case_no": "MUT-2007-1130/Keraniganj",
                "applicant_name": "Habibur Ali",
                "status": "APPROVED",
                "notes": "Mutation approved; khatian field absent on physical order sheet.",
            },
        },
    ]
    with open(os.path.join(TEXT_DATA_DIR, "registration_mutation_mismatch_pairs.json"), "w", encoding="utf-8") as f:
        json.dump(mismatch_pairs, f, indent=2, ensure_ascii=False)

    # 5. Negative controls
    neg_controls = [
        {
            "control_id": "NC-01",
            "filename": "restaurant_menu.png",
            "category": "Commercial Food Menu",
            "sample_text": "Coffee Shop Menu\nEspresso: 120 BDT\nCappuccino: 180 BDT\nTotal: 300 BDT",
            "expected_detection": "UNRELATED_DOCUMENT",
            "gatekeeper_action": "REJECT_WITH_HTTP_422",
            "message": "Document Not Recognized as a Land Record",
        },
        {
            "control_id": "NC-02",
            "filename": "retail_invoice.png",
            "category": "Retail POS Cash Receipt",
            "sample_text": "SUPER SHOP POS\nItem: Shampoo 200ml - 450 BDT\nTotal Amount: 450 BDT\nThank you for shopping",
            "expected_detection": "UNRELATED_DOCUMENT",
            "gatekeeper_action": "REJECT_WITH_HTTP_422",
            "message": "Document Not Recognized as a Land Record",
        },
    ]
    with open(os.path.join(TEXT_DATA_DIR, "negative_control_payloads.json"), "w", encoding="utf-8") as f:
        json.dump(neg_controls, f, indent=2, ensure_ascii=False)

    # 6. CSV spreadsheet of all test case inputs
    csv_path = os.path.join(TEXT_DATA_DIR, "manual_test_cases_inputs.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "test_id", "title", "document_type", "document_ref", "dag_plot_number",
            "transferred_area_decimal", "seller_nid", "buyer_nid", "mouza",
            "expected_outcome", "expected_rules", "evidence_type", "p3_requirement"
        ])
        for tcid, data in ground_truth.items():
            rules_str = "; ".join(data.get("expected_rules", [])) if "expected_rules" in data else ""
            writer.writerow([
                tcid,
                data.get("title", ""),
                data.get("document_type", ""),
                data.get("deed_number", "") or data.get("mutation_case_no", "") or data.get("khatian_number", "") or data.get("filename", ""),
                data.get("dag_plot_number", ""),
                data.get("transferred_area_decimal", ""),
                data.get("seller_nid", ""),
                data.get("buyer_nid", ""),
                data.get("mouza", ""),
                data.get("expected_outcome", ""),
                rules_str,
                data.get("evidence_type", ""),
                data.get("p3_requirement", ""),
            ])

    # 7. Raw OCR transcription dump for all 19 image samples
    raw_ocr_dump = {}
    svc = LandGuardVerificationService()
    for fname in sorted(os.listdir(SAMPLES_DIR)):
        if not fname.endswith(".png"):
            continue
        p = os.path.join(SAMPLES_DIR, fname)
        with open(p, "rb") as fp:
            b = fp.read()
        try:
            up = svc.process_document_upload(b, fname)
            raw_ocr_dump[fname] = {
                "document_type": up.get("document_type"),
                "extracted_fields": up.get("extracted_fields"),
                "confidence": up.get("confidence"),
                "raw_ocr_text_preview": up.get("raw_ocr_text", "")[:300],
            }
        except ValueError as ve:
            raw_ocr_dump[fname] = {
                "document_type": "UNRELATED_DOCUMENT",
                "error": str(ve),
                "rejected": True,
            }
        except Exception as ex:
            raw_ocr_dump[fname] = {
                "error": str(ex),
            }

    with open(os.path.join(TEXT_DATA_DIR, "raw_ocr_extracted_transcriptions.json"), "w", encoding="utf-8") as f:
        json.dump(raw_ocr_dump, f, indent=2, ensure_ascii=False)

    # 8. README.md in text_data
    text_readme_md = """# LandGuard Manual Test 3 — Structured Text Data & Ground Truth Payloads

This directory contains structured, machine-readable representations of test inputs, ground-truth payloads, chronological transfer chains, double-selling conflict pairs, registration-mutation mismatch pairs, and negative control documents.

## Directory Contents

| File | Format | Description | Primary Use Case |
|---|---|---|---|
| `ground_truth_payloads.json` | JSON | Authoritative field values for all 25 test cases (TC-01 through TC-25) | Programmatic validation and ground truth comparison |
| `raw_ocr_extracted_transcriptions.json` | JSON | Actual OCR extraction output and field parsing for all 19 image samples | Verifying vision pipeline extraction accuracy |
| `chronological_transfer_chains.json` | JSON | Multi-step historical transfer sequences on Plot 5083 and Plot 8210 | Rapid transfer velocity and double-selling simulation |
| `double_selling_conflict_pairs.json` | JSON | Legitimate vs conflicting second-sale transaction pairs | LandTech P3 Requirement 2 verification |
| `registration_mutation_mismatch_pairs.json` | JSON | Sub-Registry deed vs AC Land mutation order discrepancy pairs | LandTech P3 Requirement 4 verification |
| `negative_control_payloads.json` | JSON | Non-land documents (restaurant menu, retail receipt) and expected rejection payloads | LandGuard CyberScan gatekeeper integrity verification |
| `manual_test_cases_inputs.csv` | CSV | Tabular test input parameters ready for manual copy-paste into LandGuard web form | Human browser testing via `/verify/direct` |

## How to Use for Manual Form Testing

When testing the LandGuard statutory verification form manually without uploading an image:
1. Open the LandGuard application in your browser: `http://localhost:8000/verify`.
2. Click **Manual Verification Form** or navigate to `http://localhost:8000/verify/direct`.
3. Select the appropriate **Document Type** (e.g. `Deed of Sale`, `Mutation Order`, or `Khatian`).
4. Copy the parameters directly from `manual_test_cases_inputs.csv` or `ground_truth_payloads.json` into the corresponding form inputs.
5. Click **Run Statutory Verification** and compare the displayed results with the expected findings in `EXPECTED_RESULTS_REFERENCE.md`.

## Data Integrity & Compliance Notice

All identifiers (`SYN-XXXXXXXXXX`), citizen names, and deed references in these files are strictly synthetic demonstration data generated for the Daffodil International University (DIU) LandTech 2026 Hackathon. No real citizen personal data (PII) or real-world non-public government records are contained herein.
"""
    with open(os.path.join(TEXT_DATA_DIR, "README.md"), "w", encoding="utf-8") as f:
        f.write(text_readme_md)

    md_to_pdf(os.path.join(TEXT_DATA_DIR, "README.md"), os.path.join(TEXT_DATA_DIR, "README.pdf"), title="Text Data Guide")
    print("Generated all files in text_data/")


def generate_sample_index():
    """Generates samples/SAMPLE_INDEX.md and samples/SAMPLE_INDEX.pdf."""
    index_md = """# LandGuard Manual Test 3 — Verified Sample Image Index

This directory contains 19 verified sample document images covering all document types, statutory rules, and official Problem P3 requirements for the Daffodil International University (DIU) LandTech 2026 Innovation Hackathon.

## Master Sample Catalog

| Sample Filename | Document Type | Document Number | Dag / Plot | Transferred Area | Applicable P3 Requirement | Expected Statutory Status | Evidence Type |
|---|---|---|---|---|---|---|---|
| `IMG-025DAECA.png` | SALE_DEED | DEED-2005-23539 | 8210 | 31.82 dec | Req 2: Double-Selling / Conflicting Disposition | CONFIRMED_INCONSISTENCY | A / B |
| `IMG-04A1B22B.png` | MUTATION_RECORD | MUT-2006-5364/Rupsha | 7873 | 81.95 dec | Req 4: Registration vs Mutation Mismatch | CONFIRMED_INCONSISTENCY | A / B |
| `IMG-24DCC9AE.png` | TAX_RECEIPT | N/A (Dakhila) | 7873 | 8.38 dec | Tax Record Cross-Verification | CLEAR_FOR_STANDARD_PROCESSING | A / B |
| `IMG-24F00A6A.png` | MUTATION_RECORD | MUT-2002-9083/Keraniganj | 4603 | 18.62 dec | Req 4: Mutation Ingestion & Provenance | CLEAR_FOR_STANDARD_PROCESSING | A / B |
| `IMG-25C63DC9.png` | PARCEL_MAP / KHATIAN | Map #969 | 969 | N/A | Cadastral Boundary Verification | CLEAR_FOR_STANDARD_PROCESSING | A / B |
| `IMG-31ECD542.png` | SALE_DEED | DEED-2022-13567 | 3732 | 9.14 dec | Historical Archive / Unindexed Plot | MISSING_EVIDENCE | A / B |
| `IMG-3B9DB44D.png` | SALE_DEED | DEED-2005-20185 | 9044 | 87.25 dec | Historical Unindexed Rural Plot | MISSING_EVIDENCE | A / B |
| `IMG-3F674C0B.png` | SALE_DEED | DEED-2011-41265 | 4099 | 69.64 dec | Statutory Capacity Excess Contradiction | CONFIRMED_INCONSISTENCY | A / B |
| `IMG-4F67AAA0.png` | SALE_DEED | DEED-2001-35323 | 9044 | 9.24 dec | Statutory Transfer Baseline | CONFIRMED_INCONSISTENCY | A / B |
| `IMG-8B4D3063.png` | SALE_DEED | DEED-2012-85693 | 675 | 203.89 dec | Statutory Area Excess Contradiction | CONFIRMED_INCONSISTENCY | A / B |
| `IMG-977F14CF.png` | TAX_RECEIPT | Tax Dakhila | 9044 | 9.24 dec | Boundary Disambiguation | CLEAR_FOR_STANDARD_PROCESSING | A / B |
| `IMG-C4911827.png` | KHATIAN_PORCHA | Porcha #358 | 358 | 78.84 dec | Cadastral Record of Rights | CLEAR_FOR_STANDARD_PROCESSING | A / B |
| `IMG-E682210A.png` | KHATIAN_PORCHA | Porcha #8593 | 8593 | 16.47 dec | Cadastral Survey Rights | CLEAR_FOR_STANDARD_PROCESSING | A / B |
| `IMG-EXP-0013.png` | SALE_DEED | DEED-2021-65260 | 5235 | 15.00 dec | Req 1: Altered / Tampered Document | CONFIRMED_INCONSISTENCY | A (Vision Engine) |
| `IMG-EXP-0014.png` | SALE_DEED | DEED-2018-91244 | 6202 | 49.98 dec | Req 1: Missing Mandatory Seal | CONFIRMED_INCONSISTENCY | A / B |
| `IMG-F0EA2687.png` | MUTATION_RECORD | MUT-2001-9502/Rupsha | 9044 | 9.24 dec | Req 4: Clean Mutation Record | CLEAR_FOR_STANDARD_PROCESSING | A / B |
| `IMG-F79D53F3.png` | MUTATION_RECORD | MUT-2007-1130/Keraniganj | 2438 | 59.95 dec | Req 4: Mutation Applicant Verification | CLEAR_FOR_STANDARD_PROCESSING | A / B |
| `restaurant_menu.png` | UNRELATED_DOCUMENT | N/A | N/A | N/A | CyberScan Gatekeeper Control | REJECTED_AT_INGESTION (422) | A |
| `retail_invoice.png` | UNRELATED_DOCUMENT | N/A | N/A | N/A | CyberScan Gatekeeper Control | REJECTED_AT_INGESTION (422) | A |

## Detailed Sample Profiles

### 1. IMG-025DAECA.png — TC-04 Double-Selling Detection on Plot 8210 (TC-04 Fixed)
- **Document Type:** Deed of Sale (সাফ-কবলা দলিল)
- **Deed Number:** `DEED-2005-23539`
- **Dag / Plot Number:** `8210` (Extracted via DBNet / RapidOCR with `EXPLICIT_LABEL` provenance)
- **Transferred Area:** `31.82` decimal
- **Parties:** Seller `SYN-4713493618` (Syed Islam) & Buyer `SYN-1671902294` (Nasreen Haque)
- **Location:** Mouza Fatehabad, Upazila Hathazari, District Chattogram, JL No 76
- **Canonical Parcel Ground Truth:** Plot 8210 total recorded capacity is `19.84` decimal.
- **Expected Verification Findings:**
  - Status: `CONFIRMED_INCONSISTENCY`
  - Triggered Rules: `RULE_AREA_EXCEEDS_CAPACITY` (Claims 31.82 dec against 19.84 dec capacity) and `RULE_SELLER_NOT_TITLEHOLDER` (Seller `SYN-4713493618` does not hold current statutory title on Plot 8210).
  - ML Risk Score: `> 0.95` (Tier 4 / Critical Fraud Alert).
- **OCR Technical Note:** Tesseract previously segmented `Dag` as `059` and misread `8210` as `6210`. The generalized DBNet fusion and punctuation normalization fix extracts Plot `8210` cleanly with confidence 0.90.

### 2. IMG-04A1B22B.png — TC-10 Registration vs Mutation Record Mismatch
- **Document Type:** Mutation Order (নামজারি ও জমাভাগ আদেশ)
- **Mutation Case Number:** `MUT-2006-5364/Rupsha`
- **Dag / Plot Number:** `7873`
- **Transferred Area:** `81.95` decimal
- **Order Status:** `PENDING` (বিচারাধীন / অনিষ্পন্ন)
- **Expected Verification Findings:**
  - Status: `CONFIRMED_INCONSISTENCY`
  - Triggered Rules: `RULE_UNVERIFIED_MUTATION_RECORD` (Mutation case is marked PENDING; statutory title cannot pass until final AC Land sanction).

### 3. IMG-3F674C0B.png — TC-13 Case A Statutory Area Excess Contradiction
- **Document Type:** Deed of Sale (সাফ-কবলা দলিল)
- **Deed Number:** `DEED-2011-41265`
- **Dag / Plot Number:** `4099`
- **Transferred Area:** `69.64` decimal
- **Canonical Parcel Ground Truth:** Plot 4099 total recorded capacity is `29.66` decimal.
- **Expected Verification Findings:**
  - Status: `CONFIRMED_INCONSISTENCY`
  - Triggered Rules: `RULE_AREA_EXCEEDS_CAPACITY` (69.64 dec transferred on 29.66 dec capacity) and `RULE_SELLER_NOT_TITLEHOLDER`.

### 4. IMG-24F00A6A.png — TC-12 Real Mutation Ingestion with Full Auto-Fill
- **Document Type:** Mutation Order (নামজারি ও জমাভাগ আদেশ)
- **Mutation Case Number:** `MUT-2002-9083/Keraniganj`
- **Dag / Plot Number:** `4603`
- **Recorded Area:** `18.62` decimal
- **Order Status:** `APPROVED`
- **Expected Verification Findings:**
  - Status: `CLEAR_FOR_STANDARD_PROCESSING`
  - All form fields populate automatically from OCR with green provenance tags.

### 5. IMG-EXP-0013.png — TC-06 Altered / Tampered Document
- **Document Type:** Deed of Sale (সাফ-কবলা দলিল)
- **Deed Number:** `DEED-2021-65260`
- **Visual Tampering:** Synthetic text paste-over artifact adjacent to plot number boundary.
- **Expected Verification Findings:**
  - Status: `CONFIRMED_INCONSISTENCY`
  - Triggered Rules: `RULE_VISUAL_TAMPERING_DETECTED` (Visual anomaly and local contrast variance triggered by computer vision tamper detector).

### 6. restaurant_menu.png & retail_invoice.png — Negative Controls
- **Expected Ingestion Behavior:** Upload is rejected immediately at the CyberScan gatekeeper with HTTP status code `422 Unprocessable Entity`.
- **User Error Display:** "Document Not Recognized as a Land Record. Upload a recognized Bangladesh land document (Deed of Sale, Mutation Order, Khatian Porcha, or Dakhila)."
"""
    md_path = os.path.join(SAMPLES_DIR, "SAMPLE_INDEX.md")
    pdf_path = os.path.join(SAMPLES_DIR, "SAMPLE_INDEX.pdf")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(index_md)
    md_to_pdf(md_path, pdf_path, title="Verified Sample Index")
    print("Generated SAMPLE_INDEX.md and SAMPLE_INDEX.pdf")


if __name__ == "__main__":
    generate_text_data()
    generate_sample_index()
