"""Automated test suite for LandGuard Secure Document Storage and Re-examination System.
Validates:
1. File upload persists file to data/uploads/deeds/<sha256>_<safe_name> and records metadata in SQLite.
2. Document metadata and file streaming endpoints with strict ownership and RBAC enforcement.
3. Document re-examination endpoint re-analyzing stored original files with OCR & CV pipelines.
"""

import os
import io
import hashlib
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from src.landguard_web.app import app
from src.landguard_data.database import LandGuardDatabase

client = TestClient(app, follow_redirects=False)


@pytest.fixture(scope="module")
def sample_image_bytes():
    """Creates a sample test deed image in memory."""
    img = Image.new("RGB", (200, 200), color=(240, 240, 240))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture(scope="module")
def admin_session_cookie():
    res = client.post("/api/auth/demo-login?role=admin")
    assert res.status_code == 200
    return res.cookies.get("landguard_session")


@pytest.fixture(scope="module")
def citizen_session_cookie():
    res = client.post("/api/auth/demo-login?role=citizen")
    assert res.status_code == 200
    return res.cookies.get("landguard_session")


def test_document_upload_persistence_and_sqlite_record(citizen_session_cookie, sample_image_bytes):
    """Uploading a document persists it in deeds directory with SHA-256 and records in SQLite documents table."""
    c_citizen = TestClient(app, cookies={"landguard_session": citizen_session_cookie})

    expected_sha256 = hashlib.sha256(sample_image_bytes).hexdigest()

    response = c_citizen.post(
        "/api/upload",
        files={"file": ("test_deed_plot9044.png", sample_image_bytes, "image/png")},
    )
    assert response.status_code == 200
    data = response.json()

    doc_id = data["document_id"]
    assert doc_id.startswith("DOC-")
    assert data["sha256_hash"] == expected_sha256
    assert data["byte_size"] == len(sample_image_bytes)
    assert "deeds" in data["file_path"]

    # 1. Verify physical file persistence on disk
    stored_path = data["file_path"]
    assert os.path.exists(stored_path)
    with open(stored_path, "rb") as f:
        stored_bytes = f.read()
    assert hashlib.sha256(stored_bytes).hexdigest() == expected_sha256

    # 2. Verify SQLite documents table record
    db = LandGuardDatabase()
    doc_row = db.get_document(doc_id)
    assert doc_row is not None
    assert doc_row["document_id"] == doc_id
    assert doc_row["sha256_hash"] == expected_sha256
    assert doc_row["byte_size"] == len(sample_image_bytes)
    assert doc_row["uploaded_by"] == "USR-CITIZEN-001"


def test_document_metadata_and_file_streaming_rbac(admin_session_cookie, citizen_session_cookie, sample_image_bytes):
    """Test RBAC on document metadata and file retrieval endpoints."""
    c_citizen = TestClient(app, cookies={"landguard_session": citizen_session_cookie})
    c_admin = TestClient(app, cookies={"landguard_session": admin_session_cookie})

    # Upload document as citizen
    up_res = c_citizen.post(
        "/api/upload",
        files={"file": ("citizen_deed.png", sample_image_bytes, "image/png")},
    )
    doc_id = up_res.json()["document_id"]

    # 1. Anonymous access is blocked (401)
    anon_client = TestClient(app, follow_redirects=False)
    anon_res = anon_client.get(f"/api/documents/{doc_id}")
    assert anon_res.status_code == 401

    anon_file = anon_client.get(f"/api/documents/{doc_id}/file")
    assert anon_file.status_code == 401

    # 2. Citizen owner can access (200)
    owner_res = c_citizen.get(f"/api/documents/{doc_id}")
    assert owner_res.status_code == 200
    assert owner_res.json()["document_id"] == doc_id

    owner_file = c_citizen.get(f"/api/documents/{doc_id}/file")
    assert owner_file.status_code == 200
    assert len(owner_file.content) == len(sample_image_bytes)

    # 3. Admin can access any document (200)
    admin_res = c_admin.get(f"/api/documents/{doc_id}")
    assert admin_res.status_code == 200

    admin_file = c_admin.get(f"/api/documents/{doc_id}/file")
    assert admin_file.status_code == 200


def test_document_reanalysis_workflow(citizen_session_cookie, sample_image_bytes):
    """Test re-examination of an existing stored deed document."""
    c_citizen = TestClient(app, cookies={"landguard_session": citizen_session_cookie})

    up_res = c_citizen.post(
        "/api/upload",
        files={"file": ("reanalysis_deed.png", sample_image_bytes, "image/png")},
    )
    doc_id = up_res.json()["document_id"]

    # Trigger reanalysis
    re_res = c_citizen.post(f"/api/documents/{doc_id}/reanalyze")
    assert re_res.status_code == 200
    data = re_res.json()

    assert data["document_id"] == doc_id
    assert "reanalyzed_at" in data
    assert "extracted_fields" in data
    assert "field_confidences" in data
    assert "cv_preview" in data


def test_nonexistent_document_returns_404(citizen_session_cookie):
    """Querying non-existent document ID returns 404."""
    c_citizen = TestClient(app, cookies={"landguard_session": citizen_session_cookie})
    res = c_citizen.get("/api/documents/DOC-NONEXISTENT-999")
    assert res.status_code == 404
