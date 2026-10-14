"""Constructs document specifications across all six required LandGuard categories."""

import uuid
import random
from typing import Dict, Any, List

WATERMARK = "SYNTHETIC DEMO — NOT AN OFFICIAL DOCUMENT"


def build_sale_deed_document(
    txn: Dict[str, Any],
    parcel: Dict[str, Any],
    seller: Dict[str, Any],
    buyer: Dict[str, Any],
    template_id: str,
    lang: str = "bn"
) -> Dict[str, Any]:
    uid = uuid.UUID(int=random.getrandbits(128)).hex[:8].upper()
    
    fields = {
        "deed_number": txn["deed_number"],
        "execution_date": txn["execution_date"],
        "seller_name_en": seller["full_name_en"],
        "seller_name_bn": seller["full_name_bn"],
        "seller_nid": seller["fictional_nid"],
        "buyer_name_en": buyer["full_name_en"],
        "buyer_name_bn": buyer["full_name_bn"],
        "buyer_nid": buyer["fictional_nid"],
        "district": parcel["district"],
        "upazila": parcel["upazila"],
        "mouza": parcel["mouza"],
        "jl_number": str(parcel["jl_number"]),
        "dag_plot_number": str(parcel["dag_plot_number"]),
        "transferred_area_decimal": f"{txn['transferred_area_decimal']:.2f}",
        "land_classification": parcel["land_classification"],
        "consideration_bdt": f"{txn['consideration_bdt']:,.2f}",
        "sub_registry_office": txn["registration_sub_office"],
        "boundary_north": parcel["boundaries"]["north"],
        "boundary_south": parcel["boundaries"]["south"],
        "has_seal": not txn.get("seal_omitted", False),
        "has_signature": True
    }
    
    return {
        "document_id": f"DOC-{uid}",
        "document_type": "SALE_DEED",
        "language": lang,
        "template_id": template_id,
        "canonical_record_id": txn["transaction_id"],
        "parcel_id": parcel["parcel_id"],
        "watermark_text": WATERMARK,
        "fields": fields,
        "created_at": txn["execution_date"],
        "is_synthetic": True
    }


def build_khatian_document(
    khatian: Dict[str, Any],
    parcel: Dict[str, Any],
    owners_map: Dict[str, Any],
    template_id: str,
    lang: str = "bn"
) -> Dict[str, Any]:
    uid = uuid.UUID(int=random.getrandbits(128)).hex[:8].upper()
    
    owner_lines = []
    for o in khatian["owners"]:
        ow = owners_map.get(o["owner_id"])
        name = ow["full_name_bn"] if ow else o["owner_id"]
        owner_lines.append(f"{name} ({o['share_fraction']*16:.2f} আনা / {o['share_fraction']:.4f})")
        
    fields = {
        "khatian_type": khatian["khatian_type"],
        "khatian_number": str(khatian["khatian_number"]),
        "district": parcel["district"],
        "upazila": parcel["upazila"],
        "mouza": parcel["mouza"],
        "jl_number": str(parcel["jl_number"]),
        "dag_plot_number": str(parcel["dag_plot_number"]),
        "total_area_decimal": f"{parcel['total_area_decimal']:.2f}",
        "land_classification": parcel["land_classification"],
        "effective_year": str(khatian["effective_year"]),
        "owners_text": " ; ".join(owner_lines),
        "status": khatian["status"]
    }
    
    return {
        "document_id": f"DOC-{uid}",
        "document_type": "KHATIAN_PORCHA",
        "language": lang,
        "template_id": template_id,
        "canonical_record_id": khatian["record_id"],
        "parcel_id": parcel["parcel_id"],
        "watermark_text": WATERMARK,
        "fields": fields,
        "created_at": f"{khatian['effective_year']}-01-01",
        "is_synthetic": True
    }


def build_mutation_document(
    mut: Dict[str, Any],
    parcel: Dict[str, Any],
    prev_owner: Dict[str, Any],
    new_owner: Dict[str, Any],
    template_id: str,
    lang: str = "bn"
) -> Dict[str, Any]:
    uid = uuid.UUID(int=random.getrandbits(128)).hex[:8].upper()
    
    fields = {
        "mutation_case_no": mut["mutation_case_no"],
        "effective_date": mut["effective_date"],
        "previous_owner_bn": prev_owner["full_name_bn"],
        "new_owner_bn": new_owner["full_name_bn"],
        "new_owner_en": new_owner["full_name_en"],
        "district": parcel["district"],
        "upazila": parcel["upazila"],
        "mouza": parcel["mouza"],
        "dag_plot_number": str(parcel["dag_plot_number"]),
        "transferred_area_decimal": f"{parcel['total_area_decimal']:.2f}",
        "status": mut["status"],
        "has_seal": True,
        "has_signature": True
    }
    
    return {
        "document_id": f"DOC-{uid}",
        "document_type": "MUTATION_RECORD",
        "language": lang,
        "template_id": template_id,
        "canonical_record_id": mut["mutation_id"],
        "parcel_id": parcel["parcel_id"],
        "watermark_text": WATERMARK,
        "fields": fields,
        "created_at": mut["effective_date"],
        "is_synthetic": True
    }


def build_tax_receipt_document(
    tax: Dict[str, Any],
    parcel: Dict[str, Any],
    owner: Dict[str, Any],
    template_id: str,
    lang: str = "bn"
) -> Dict[str, Any]:
    uid = uuid.UUID(int=random.getrandbits(128)).hex[:8].upper()
    
    fields = {
        "receipt_no": tax["receipt_no"],
        "tax_year": str(tax["tax_year"]),
        "owner_name_bn": owner["full_name_bn"],
        "district": parcel["district"],
        "upazila": parcel["upazila"],
        "mouza": parcel["mouza"],
        "dag_plot_number": str(parcel["dag_plot_number"]),
        "area_decimal": f"{parcel['total_area_decimal']:.2f}",
        "assessed_bdt": f"{tax['assessed_bdt']:.2f}",
        "paid_bdt": f"{tax['paid_bdt']:.2f}",
        "payment_status": tax["payment_status"],
        "has_seal": True
    }
    
    return {
        "document_id": f"DOC-{uid}",
        "document_type": "TAX_RECEIPT",
        "language": lang,
        "template_id": template_id,
        "canonical_record_id": tax["receipt_id"],
        "parcel_id": parcel["parcel_id"],
        "watermark_text": WATERMARK,
        "fields": fields,
        "created_at": f"{tax['tax_year']}-06-30",
        "is_synthetic": True
    }


def build_parcel_map_document(
    parcel: Dict[str, Any],
    template_id: str,
    lang: str = "en"
) -> Dict[str, Any]:
    uid = uuid.UUID(int=random.getrandbits(128)).hex[:8].upper()
    
    fields = {
        "map_title": f"Cadastral Plot Map — Mouza: {parcel['mouza']}, JL #{parcel['jl_number']}",
        "dag_plot_number": str(parcel["dag_plot_number"]),
        "total_area_decimal": f"{parcel['total_area_decimal']:.2f}",
        "scale": "1:1000",
        "north_boundary": parcel["boundaries"]["north"],
        "south_boundary": parcel["boundaries"]["south"],
        "east_boundary": parcel["boundaries"]["east"],
        "west_boundary": parcel["boundaries"]["west"]
    }
    
    return {
        "document_id": f"DOC-{uid}",
        "document_type": "PARCEL_MAP",
        "language": lang,
        "template_id": template_id,
        "canonical_record_id": parcel["parcel_id"],
        "parcel_id": parcel["parcel_id"],
        "watermark_text": WATERMARK,
        "fields": fields,
        "created_at": "2024-01-01",
        "is_synthetic": True
    }


def build_application_document(
    parcel: Dict[str, Any],
    applicant: Dict[str, Any],
    template_id: str,
    lang: str = "bn"
) -> Dict[str, Any]:
    uid = uuid.UUID(int=random.getrandbits(128)).hex[:8].upper()
    
    fields = {
        "application_no": f"APP-2024-{random.randint(1000, 9999)}",
        "date": "2024-05-14",
        "applicant_name_bn": applicant["full_name_bn"],
        "applicant_nid": applicant["fictional_nid"],
        "subject": "জমি খারিজ ও নামজারি সংক্রান্ত আবেদন (Application for Land Mutation)",
        "district": parcel["district"],
        "upazila": parcel["upazila"],
        "mouza": parcel["mouza"],
        "dag_plot_number": str(parcel["dag_plot_number"]),
        "narrative": f"বিনীত নিবেদন এই যে, আমি নিম্নস্বাক্ষরকারী মৌজা {parcel['mouza']}-এর দাগ নং {parcel['dag_plot_number']} খাস জমি বা বৈধ খতিয়ানমূলে মালিকানা প্রাপ্ত হইয়া নামজারি ও জমাভাগ করণের আবেদন করিতেছি।",
        "status": "PENDING_HEARING",
        "has_signature": True
    }
    
    return {
        "document_id": f"DOC-{uid}",
        "document_type": "APPLICATION_COMPLAINT",
        "language": lang,
        "template_id": template_id,
        "canonical_record_id": f"APP-{uid}",
        "parcel_id": parcel["parcel_id"],
        "watermark_text": WATERMARK,
        "fields": fields,
        "created_at": "2024-05-14",
        "is_synthetic": True
    }
