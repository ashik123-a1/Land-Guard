"""LandGuard Web Schemas
Pydantic models for API request bodies and payloads.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str
    password: str
    redirect: Optional[str] = None


class VerifyRequest(BaseModel):
    confirmed_fields: Dict[str, Any] = Field(..., description="User-reviewed legal deed fields")
    document_type: Optional[str] = Field("SALE_DEED", description="Classified document type (SALE_DEED, MUTATION_RECORD, KHATIAN_PORCHA, TAX_RECEIPT, PARCEL_MAP, UNCERTAIN)")
    image_path: Optional[str] = Field(None, description="Path or identifier of uploaded document image")
    evidence_source: Optional[str] = Field("UPLOAD", description="Provenance of evidence: BENCHMARK, UPLOAD, or MANUAL")
    original_ocr_fields: Optional[Dict[str, Any]] = Field(None, description="Original unedited OCR fields for diff audit")


class CreateCaseRequest(BaseModel):
    title: Optional[str] = None
    deed_number: Optional[str] = "N/A"
    dag_plot_number: Optional[str] = "N/A"
    verification_id: Optional[str] = None
    priority: Optional[str] = "HIGH"
    assigned_officer: Optional[str] = "Unassigned"
    statutory_finding: Optional[str] = "REVIEW_REQUIRED"
    ml_risk_score: Optional[float] = None
    evidence_summary: Optional[str] = ""
    initial_note: Optional[str] = "Case initialized from LandGuard verification finding."


class UpdateCaseRequest(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_officer: Optional[str] = None
    evidence_summary: Optional[str] = None
    title: Optional[str] = None


class AddCaseNoteRequest(BaseModel):
    note: str
    author: Optional[str] = "Officer"


class CreateComplaintRequest(BaseModel):
    category: str
    dag_plot_number: str
    deed_number: str
    title: str
    narrative_description: str
    is_expedited: Optional[bool] = False
    expedite_reason: Optional[str] = None


class ExpediteRequestPayload(BaseModel):
    reason: str
    reason_category: Optional[str] = None



class ExpediteDecisionPayload(BaseModel):
    decision: str
    reason: str


class VerificationDecisionRequest(BaseModel):
    decision: str
    reason: str


class UpdateReportStatusRequest(BaseModel):
    status: str
    reason: Optional[str] = None


class VoiceIntentRequest(BaseModel):
    text: str
    language: Optional[str] = "auto"


class CaseClarificationRequest(BaseModel):
    question: str


class CaseClarificationResponse(BaseModel):
    response: str


class WhatIfSimulationRequest(BaseModel):
    dag_plot_number: str
    seller_nid: str
    buyer_nid: str
    transferred_area_decimal: float
    consideration_bdt: Optional[float] = 0.0
    previous_deed_ref: Optional[str] = None
    mutation_case_no: Optional[str] = None
