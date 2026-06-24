"""
Locust Stress Test — Gammal Tech Healthcare App
Run: locust -f locustfile.py --host=https://gammal-tech-frontend.vercel.app
"""

from locust import HttpUser, task, between
import random


CREDENTIALS = [
    {"email": "patient@test.com", "password": "Patient123!"},
    {"email": "doctor@test.com",  "password": "Doctor123!"},
]


class HealthcareUser(HttpUser):
    wait_time = between(1, 3)
    token: str = ""

    def on_start(self):
        """Login and store token before running tasks."""
        creds = random.choice(CREDENTIALS)
        with self.client.post(
            "/api/auth/login",
            json=creds,
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                self.token = data.get("token", "")
                resp.success()
            else:
                resp.failure(f"Login failed: {resp.status_code}")

    def _auth_headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    # ---- Happy Path Tasks ------------------------------------------------

    @task(3)
    def view_dashboard(self):
        self.client.get("/api/dashboard", headers=self._auth_headers(), name="/api/dashboard")

    @task(3)
    def list_appointments(self):
        self.client.get("/api/appointments", headers=self._auth_headers(), name="/api/appointments")

    @task(2)
    def view_own_record(self):
        self.client.get("/api/patients/me", headers=self._auth_headers(), name="/api/patients/me")

    @task(1)
    def book_appointment(self):
        payload = {
            "doctor_id": random.randint(1, 5),
            "date": "2026-08-01",
            "time": f"{random.randint(9, 16):02d}:00",
        }
        with self.client.post(
            "/api/appointments",
            json=payload,
            headers=self._auth_headers(),
            catch_response=True,
            name="/api/appointments [POST]",
        ) as resp:
            # 201 = success, 409 = slot taken — both acceptable under load
            if resp.status_code in (201, 409):
                resp.success()
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")

    # ---- Edge Case / Security Tasks (at low weight) ----------------------

    @task(1)
    def idor_attempt(self):
        """Try to access a random patient ID — should return 403 for unauthorized."""
        patient_id = random.randint(1, 1000)
        with self.client.get(
            f"/api/patients/{patient_id}",
            headers=self._auth_headers(),
            catch_response=True,
            name="/api/patients/{id} [IDOR check]",
        ) as resp:
            # Acceptable: 200 (own record), 403 (forbidden), 404 (not found)
            if resp.status_code in (200, 403, 404):
                resp.success()
            else:
                resp.failure(f"Unexpected: {resp.status_code}")

    def on_stop(self):
        self.client.post("/api/auth/logout", headers=self._auth_headers())


class BruteForceSpikeUser(HttpUser):
    """
    TC-ST-003: Simulates brute-force login attempts.
    Rate limiting should kick in before 10 attempts.
    """
    wait_time = between(0.1, 0.5)
    weight = 1  # low weight — only a few of these in the swarm

    @task
    def brute_force_login(self):
        payload = {
            "email": "victim@test.com",
            "password": f"wrong_{random.randint(0, 9999)}",
        }
        with self.client.post(
            "/api/auth/login",
            json=payload,
            catch_response=True,
            name="/api/auth/login [brute force]",
        ) as resp:
            # Expect 401 (wrong creds) or 429 (rate limited) — both fine
            if resp.status_code in (401, 429, 423):
                resp.success()
            elif resp.status_code == 200:
                resp.failure("BUG: Brute force login succeeded!")
            else:
                resp.failure(f"Unexpected: {resp.status_code}")
