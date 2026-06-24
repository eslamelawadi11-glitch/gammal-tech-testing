"""
pytest API Test Suite — Gammal Tech Healthcare App
TC-EC-* and TC-HP-* automated API tests

Install: pip install pytest requests
Run: pytest tests/ -v
"""

import pytest
import requests

BASE_URL = "https://gammal-tech-frontend.vercel.app/api"


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def patient_token():
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "patient@test.com",
        "password": "Patient123!"
    })
    assert resp.status_code == 200, f"Patient login failed: {resp.text}"
    return resp.json()["token"]


@pytest.fixture(scope="module")
def admin_token():
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "admin@test.com",
        "password": "Admin123!"
    })
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    return resp.json()["token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ─── TC-HP: Happy Path Tests ───────────────────────────────────────────────────

class TestHappyPath:

    def test_hp001_login_patient(self):
        """TC-HP-001: Valid patient login returns 200 + token."""
        resp = requests.post(f"{BASE_URL}/auth/login", json={
            "email": "patient@test.com",
            "password": "Patient123!"
        })
        assert resp.status_code == 200
        body = resp.json()
        assert "token" in body, "No token in response"
        assert len(body["token"]) > 20, "Token too short"

    def test_hp002_register_new_user(self):
        """TC-HP-002: New registration returns 201."""
        import time
        unique_email = f"newuser_{int(time.time())}@test.com"
        resp = requests.post(f"{BASE_URL}/auth/register", json={
            "name": "Test User",
            "email": unique_email,
            "password": "StrongPass123!",
            "age": 30,
            "gender": "male"
        })
        assert resp.status_code in (200, 201), f"Register failed: {resp.text}"

    def test_hp003_view_own_record(self, patient_token):
        """TC-HP-003: Authenticated patient can view own record."""
        resp = requests.get(f"{BASE_URL}/patients/me", headers=auth(patient_token))
        assert resp.status_code == 200
        body = resp.json()
        assert "id" in body or "patient_id" in body

    def test_hp004_list_appointments(self, patient_token):
        """TC-HP-004: Authenticated patient can list their appointments."""
        resp = requests.get(f"{BASE_URL}/appointments", headers=auth(patient_token))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_hp007_logout_invalidates_token(self, patient_token):
        """TC-HP-007: After logout, token should be rejected."""
        logout = requests.post(f"{BASE_URL}/auth/logout", headers=auth(patient_token))
        assert logout.status_code in (200, 204)

        # Now use the old token — should be refused
        resp = requests.get(f"{BASE_URL}/patients/me", headers=auth(patient_token))
        assert resp.status_code in (401, 403), (
            f"Stale token still works after logout! Got {resp.status_code}"
        )


# ─── TC-EC: Edge Case Tests ────────────────────────────────────────────────────

class TestEdgeCases:

    def test_ec001_login_unregistered_email(self):
        """TC-EC-001: Unregistered email returns 401, no user enumeration."""
        resp = requests.post(f"{BASE_URL}/auth/login", json={
            "email": "ghost_9999999@nowhere.com",
            "password": "anything"
        })
        assert resp.status_code == 401
        body = resp.text.lower()
        assert "not found" not in body, "User enumeration: 'not found' in response"
        assert "does not exist" not in body, "User enumeration: 'does not exist' in response"

    def test_ec002_register_duplicate_email(self):
        """TC-EC-002: Registering existing email returns 409."""
        resp = requests.post(f"{BASE_URL}/auth/register", json={
            "name": "Dup User",
            "email": "patient@test.com",
            "password": "StrongPass123!",
            "age": 25,
            "gender": "female"
        })
        assert resp.status_code == 409, f"Expected 409 for duplicate email, got {resp.status_code}"

    @pytest.mark.parametrize("weak_password", ["123", "password", "aaaaaa", "abc"])
    def test_ec003_weak_password_blocked(self, weak_password):
        """TC-EC-003: Weak passwords rejected on registration."""
        import time
        resp = requests.post(f"{BASE_URL}/auth/register", json={
            "name": "Weak User",
            "email": f"weak_{int(time.time())}@test.com",
            "password": weak_password,
            "age": 20,
            "gender": "male"
        })
        assert resp.status_code == 400, (
            f"Weak password '{weak_password}' was accepted! Status: {resp.status_code}"
        )

    @pytest.mark.parametrize("payload", [
        "' OR '1'='1",
        "' OR 1=1--",
        "admin'--",
        '" OR ""="',
        "1; DROP TABLE users--",
    ])
    def test_ec004_sql_injection_login(self, payload):
        """TC-EC-004: SQL injection payloads in login fields return 400/401, never 200."""
        resp = requests.post(f"{BASE_URL}/auth/login", json={
            "email": payload,
            "password": payload
        })
        assert resp.status_code in (400, 401, 422), (
            f"SQLi payload accepted! Status: {resp.status_code}, payload: {payload}"
        )
        body = resp.text.lower()
        sql_errors = ["sql", "syntax error", "mysql", "postgresql", "ora-", "sqlite"]
        for err in sql_errors:
            assert err not in body, f"SQL error exposed: '{err}' found in response"

    @pytest.mark.parametrize("xss_payload", [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert(1)>",
        "javascript:alert(1)",
        '"><svg/onload=alert(1)>',
    ])
    def test_ec005_xss_in_name_field(self, admin_token, xss_payload):
        """TC-EC-005: XSS payloads stored as escaped text, not raw HTML."""
        update = requests.put(
            f"{BASE_URL}/patients/me",
            json={"name": xss_payload},
            headers=auth(admin_token)
        )
        assert update.status_code in (200, 201, 400), f"Unexpected: {update.status_code}"

        if update.status_code in (200, 201):
            get = requests.get(f"{BASE_URL}/patients/me", headers=auth(admin_token))
            returned_name = get.json().get("name", "")
            # Raw script tag should never come back unescaped
            assert "<script>" not in returned_name, f"XSS not escaped: {returned_name}"
            assert "onerror=" not in returned_name, f"XSS not escaped: {returned_name}"

    def test_ec006_idor_patient_record(self, patient_token, admin_token):
        """TC-EC-006: Patient cannot access another patient's record (IDOR)."""
        # Get own ID
        me = requests.get(f"{BASE_URL}/patients/me", headers=auth(patient_token))
        my_id = me.json().get("id") or me.json().get("patient_id")

        # Try incrementing to another patient
        other_id = int(my_id) + 1 if my_id else 999
        resp = requests.get(f"{BASE_URL}/patients/{other_id}", headers=auth(patient_token))
        assert resp.status_code in (403, 404), (
            f"IDOR: Patient accessed record {other_id} with status {resp.status_code}"
        )

    def test_ec007_book_past_date(self, patient_token):
        """TC-EC-007: Booking in the past returns 400."""
        resp = requests.post(f"{BASE_URL}/appointments", json={
            "doctor_id": 1,
            "date": "2020-01-01",
            "time": "10:00"
        }, headers=auth(patient_token))
        assert resp.status_code == 400, (
            f"Past date accepted! Status: {resp.status_code}"
        )

    def test_ec009_empty_fields_on_register(self):
        """TC-EC-009: Missing required fields return 400."""
        resp = requests.post(f"{BASE_URL}/auth/register", json={})
        assert resp.status_code in (400, 422)

    def test_ec010_long_input_in_name(self, patient_token):
        """TC-EC-010: 10,000-char name is rejected or truncated gracefully."""
        long_name = "A" * 10000
        resp = requests.put(
            f"{BASE_URL}/patients/me",
            json={"name": long_name},
            headers=auth(patient_token)
        )
        # Should not be a 500
        assert resp.status_code != 500, "Server crashed on long input!"
        assert resp.status_code in (200, 201, 400, 422)

    def test_ec011_tampered_jwt(self):
        """TC-EC-011: Tampered JWT signature is rejected."""
        import base64, json

        # Build a fake token with role=admin
        header  = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b"=").decode()
        payload = base64.urlsafe_b64encode(
            json.dumps({"sub": "1", "role": "admin", "exp": 9999999999}).encode()
        ).rstrip(b"=").decode()
        fake_sig = "fakesignature"
        tampered_token = f"{header}.{payload}.{fake_sig}"

        resp = requests.get(
            f"{BASE_URL}/admin/users",
            headers={"Authorization": f"Bearer {tampered_token}"}
        )
        assert resp.status_code in (401, 403), (
            f"Tampered JWT accepted! Status: {resp.status_code}"
        )

    def test_ec012_no_token_rejected(self):
        """TC-EC-012: Protected endpoint without token returns 401."""
        resp = requests.get(f"{BASE_URL}/patients")
        assert resp.status_code == 401, (
            f"Unauthenticated access allowed! Status: {resp.status_code}"
        )


# ─── TC-ST: Basic Stress / Rate Limit Checks ──────────────────────────────────

class TestRateLimiting:

    def test_st003_brute_force_rate_limit(self):
        """TC-ST-003: 15 rapid wrong-password attempts trigger rate limit (429)."""
        statuses = []
        for i in range(15):
            resp = requests.post(f"{BASE_URL}/auth/login", json={
                "email": "victim@test.com",
                "password": f"wrong_{i}"
            })
            statuses.append(resp.status_code)

        rate_limited = any(s in (429, 423) for s in statuses)
        assert rate_limited, (
            f"No rate limiting detected after 15 attempts. Statuses: {statuses}"
        )
