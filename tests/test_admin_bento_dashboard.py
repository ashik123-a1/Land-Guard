"""Tests for LandGuard Admin Bento-Grid Dashboard & Analytics API
Verifies:
1. Admin Bento dashboard page rendering and elements
2. Dynamic dashboard analytics API endpoint with year filtering
3. Strict RBAC enforcement (Citizens and unauthenticated requests blocked)
4. KPI schema integrity and metric separation (never labeling model prediction as fraud)
5. 12-month time series completeness across all 5 metric views
"""

import pytest
from fastapi.testclient import TestClient
from src.landguard_web.app import app

client = TestClient(app, follow_redirects=False)


def test_admin_bento_dashboard_page_rendering():
    """Admin dashboard renders Bento-grid cards, Chart.js canvas, and controls."""
    # Login as admin
    login_res = client.post("/api/auth/demo-login?role=admin")
    assert login_res.status_code == 200
    cookie = login_res.cookies.get("landguard_session")
    admin_client = TestClient(app, cookies={"landguard_session": cookie, "landguard_lang": "en"}, follow_redirects=False)

    res = admin_client.get("/admin/dashboard")
    assert res.status_code == 200
    html = res.text

    # Title & Branding
    assert "LandGuard Intelligence" in html
    assert "Investigator Command Center" in html
    assert "Land Verification &amp; Risk Monitoring" in html or "Land Verification & Risk Monitoring" in html

    # 5 KPI Bento Cards
    assert 'id="kpiCard-verifications"' in html
    assert 'id="kpiCard-risk"' in html
    assert 'id="kpiCard-conflicts"' in html
    assert 'id="kpiCard-cases"' in html
    assert 'id="kpiCard-documents"' in html

    # Main Chart & 12-Month Timeline
    assert 'id="mainDashboardChart"' in html
    assert 'id="monthPill-all"' in html
    assert 'id="monthPill-0"' in html  # Jan
    assert 'id="monthPill-11"' in html # Dec

    # Theme Toggle & Year Controls
    assert 'id="themeToggleBtn"' in html
    assert 'id="yearBtn2026"' in html
    assert 'id="yearBtn2025"' in html
    assert 'id="yearBtnALL"' in html

    # Disclaimer & Supporting Dockets
    assert "SYNTHETIC" in html
    assert "Priority Investigation Docket" in html
    assert "Real-Time Inconsistency Alerts" in html


def test_dashboard_analytics_api_year_filtering():
    """Verify /api/admin/dashboard-analytics returns accurate 12-month data and filters by year."""
    login_res = client.post("/api/auth/demo-login?role=investigator")
    cookie = login_res.cookies.get("landguard_session")
    inv_client = TestClient(app, cookies={"landguard_session": cookie}, follow_redirects=False)

    # 1. Default year (2026)
    res_2026 = inv_client.get("/api/admin/dashboard-analytics?year=2026")
    assert res_2026.status_code == 200
    data_2026 = res_2026.json()
    assert data_2026["selected_year"] == "2026"
    assert "kpis" in data_2026
    assert "time_series" in data_2026
    assert len(data_2026["time_series"]["months"]) == 12

    # 2. Check all 5 KPI structures
    kpis = data_2026["kpis"]
    assert "verifications" in kpis
    assert "risk" in kpis
    assert "conflicts" in kpis
    assert "cases" in kpis
    assert "documents" in kpis

    # Verify model risk indicator is not labeled as confirmed fraud
    assert "model_risk_indicators" in kpis["risk"]
    assert "confirmed_inconsistencies" in kpis["risk"]
    assert kpis["risk"]["high_risk_awaiting_review"] > 0
    assert "Model indicators represent statistical anomaly scores" in kpis["risk"]["disclaimer"]

    # 3. Check all 5 Time Series views
    ts = data_2026["time_series"]
    assert len(ts["verifications"]["volume"]) == 12
    assert len(ts["verifications"]["completed"]) == 12
    assert len(ts["risk"]["model_indicators"]) == 12
    assert len(ts["risk"]["confirmed_inconsistencies"]) == 12
    assert ts["risk"]["threshold_reference"] == 0.35
    assert len(ts["conflicts"]["double_selling"]) == 12
    assert len(ts["conflicts"]["mutation_discrepancies"]) == 12
    assert len(ts["cases"]["new_cases"]) == 12
    assert len(ts["documents"]["processed"]) == 12

    # 4. Filter by 2025
    res_2025 = inv_client.get("/api/admin/dashboard-analytics?year=2025")
    assert res_2025.status_code == 200
    data_2025 = res_2025.json()
    assert data_2025["selected_year"] == "2025"
    # 2025 volume should be scaled lower than 2026
    assert sum(data_2025["time_series"]["verifications"]["volume"]) < sum(data_2026["time_series"]["verifications"]["volume"])

    # 5. Filter by ALL
    res_all = inv_client.get("/api/admin/dashboard-analytics?year=ALL")
    assert res_all.status_code == 200
    data_all = res_all.json()
    assert data_all["selected_year"] == "ALL"
    assert sum(data_all["time_series"]["verifications"]["volume"]) > sum(data_2026["time_series"]["verifications"]["volume"])


def test_dashboard_analytics_rbac_protection():
    """Citizen and unauthenticated visitors cannot access admin analytics API."""
    # 1. Unauthenticated request -> redirects to login
    fresh_client = TestClient(app, follow_redirects=False)
    unauth_res = fresh_client.get("/api/admin/dashboard-analytics")
    assert unauth_res.status_code == 303
    assert "/login" in unauth_res.headers.get("Location", "")

    # 2. Citizen request -> redirected to access-denied
    cit_client = TestClient(app, follow_redirects=False)
    cit_login = cit_client.post("/api/auth/demo-login?role=citizen")
    assert cit_login.status_code == 200

    cit_res = cit_client.get("/api/admin/dashboard-analytics")
    assert cit_res.status_code == 303
    assert "/access-denied" in cit_res.headers.get("Location", "")
