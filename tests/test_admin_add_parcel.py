"""Automated Tests for Admin Add Land Area / Parcel Functionality and Duplicate Rejection.
Verifies:
1. Admin interface exposes Add Parcel modal and duplicate safety notice.
2. Authorized admin can register new cadastral parcel into persistent storage and memory.
3. System strictly rejects duplicate dag plot numbers within the same mouza/upazila with HTTP 409 Conflict.
4. Non-admin users (citizens / unauthenticated) are blocked from registering parcels.
5. Invalid parameters (zero/negative area, empty plot #) return HTTP 400 validation errors.
"""

import pytest
from fastapi.testclient import TestClient

from src.landguard_web.app import app
from src.landguard_web.service import service

client = TestClient(app, follow_redirects=False)


@pytest.fixture(scope="module")
def admin_client():
    login_res = client.post("/api/auth/demo-login?role=admin")
    assert login_res.status_code == 200
    cookie = login_res.cookies.get("landguard_session")
    return TestClient(app, cookies={"landguard_session": cookie}, follow_redirects=False)


@pytest.fixture(scope="module")
def citizen_client():
    login_res = client.post("/api/auth/demo-login?role=citizen")
    assert login_res.status_code == 200
    cookie = login_res.cookies.get("landguard_session")
    return TestClient(app, cookies={"landguard_session": cookie}, follow_redirects=False)


def test_admin_parcels_page_renders_add_button_and_modal(admin_client):
    """Admin parcels page must display the '+ নতুন জমি যুক্ত করুন' button and registration modal."""
    res = admin_client.get("/admin/parcels")
    assert res.status_code == 200
    html = res.text

    assert "+ নতুন জমি যুক্ত করুন" in html
    assert 'id="addParcelModal"' in html
    assert 'id="parcelFormError"' in html
    assert 'id="p-plot-number"' in html
    assert 'id="p-mouza"' in html
    assert 'id="p-area-decimal"' in html
    assert "ডুপ্লিকেট" in html


def test_admin_add_parcel_success(admin_client):
    """Admin successfully registers a new unique cadastral parcel."""
    test_plot = "77881"
    payload = {
        "dag_plot_number": test_plot,
        "khatian_number": f"BS-{test_plot}",
        "mouza": "Test Mouza North",
        "jl_number": "99",
        "upazila": "Kaliakair",
        "district": "Gazipur",
        "total_area_decimal": 33.75,
        "land_classification": "Nal",
        "owner_name": "Nakib Md Ashik",
        "owner_nid": "19902692019000123",
    }

    res = admin_client.post("/admin/parcels/create", json=payload)
    assert res.status_code == 201
    data = res.json()

    assert data["success"] is True
    assert data["conflict"] is False
    assert test_plot in data["message"]
    assert data["parcel"]["dag_plot_number"] == test_plot
    assert data["parcel"]["mouza"] == "Test Mouza North"
    assert data["parcel"]["total_area_decimal"] == 33.75

    # Verify parcel is now immediately searchable in domain service
    search_results = service.search_parcels(test_plot)
    assert any(p["dag_plot_number"] == test_plot for p in search_results)

    # Verify parcel details and chain are accessible
    details = service.get_parcel_details(test_plot)
    assert details is not None
    assert details["parcel"]["dag_plot_number"] == test_plot
    assert details["parcel"]["total_area_decimal"] == 33.75


def test_duplicate_parcel_strictly_rejected_with_409_conflict(admin_client):
    """Submitting the same plot in the same mouza/upazila MUST return HTTP 409 Conflict with an explicit error."""
    test_plot = "77881"
    duplicate_payload = {
        "dag_plot_number": test_plot,
        "khatian_number": f"BS-{test_plot}-DUP",
        "mouza": "Test Mouza North",
        "jl_number": "99",
        "upazila": "Kaliakair",
        "district": "Gazipur",
        "total_area_decimal": 12.00,
        "land_classification": "Viti",
        "owner_name": "Another Person",
    }

    res = admin_client.post("/admin/parcels/create", json=duplicate_payload)
    assert res.status_code == 409
    data = res.json()

    assert data["success"] is False
    assert data["conflict"] is True
    assert "ডুপ্লিকেট" in data["error"]
    assert test_plot in data["error"]
    assert "Duplicate entry is strictly rejected" in data.get("error_en", "")


def test_existing_canonical_plot_duplicate_prevention(admin_client):
    """Attempting to add an existing canonical benchmark plot (e.g. 9044) must also be blocked with 409."""
    canonical_payload = {
        "dag_plot_number": "9044",
        "khatian_number": "BS-9044",
        "mouza": "Naihati",
        "upazila": "Rupsha",
        "district": "Khulna",
        "total_area_decimal": 20.0,
        "land_classification": "Nal",
    }

    res = admin_client.post("/admin/parcels/create", json=canonical_payload)
    assert res.status_code == 409
    data = res.json()

    assert data["conflict"] is True
    assert data["success"] is False
    assert "9044" in data["error"]
    assert "ডুপ্লিকেট" in data["error"]


def test_citizen_cannot_create_parcel(citizen_client):
    """Citizen role is strictly denied from creating parcels."""
    payload = {
        "dag_plot_number": "55555",
        "mouza": "Savar",
        "total_area_decimal": 10.0,
    }
    res = citizen_client.post("/admin/parcels/create", json=payload)
    # Either 403 Forbidden or 303 Redirect to access-denied
    assert res.status_code in (403, 303)


def test_unauthenticated_cannot_create_parcel():
    """Unauthenticated request is rejected."""
    payload = {
        "dag_plot_number": "55555",
        "mouza": "Savar",
        "total_area_decimal": 10.0,
    }
    res = client.post("/admin/parcels/create", json=payload)
    assert res.status_code in (401, 403, 303)


def test_validation_errors_zero_area_and_missing_fields(admin_client):
    """Zero or negative area and missing required fields are rejected with HTTP 400."""
    # Missing plot number
    res1 = admin_client.post("/admin/parcels/create", json={
        "dag_plot_number": "",
        "mouza": "Savar",
        "total_area_decimal": 15.0,
    })
    assert res1.status_code == 400
    assert "দাগ নম্বর" in res1.json()["error"]

    # Missing mouza
    res2 = admin_client.post("/admin/parcels/create", json={
        "dag_plot_number": "88888",
        "mouza": "",
        "total_area_decimal": 15.0,
    })
    assert res2.status_code == 400
    assert "মৌজা" in res2.json()["error"]

    # Zero area
    res3 = admin_client.post("/admin/parcels/create", json={
        "dag_plot_number": "88888",
        "mouza": "Savar",
        "total_area_decimal": 0.0,
    })
    assert res3.status_code == 400
    assert "শূন্যের চেয়ে বেশি" in res3.json()["error"]
