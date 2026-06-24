"""
Playwright E2E Tests — Happy Path
TC-HP-001, TC-HP-002, TC-HP-004, TC-HP-007

Install: pip install playwright pytest-playwright
         playwright install chromium
Run: pytest tests/test_e2e.py -v --headed
"""

import pytest
from playwright.sync_api import Page, expect

BASE = "https://gammal-tech-frontend.vercel.app"


@pytest.fixture(scope="function")
def logged_in_page(page: Page):
    """Returns a page already logged in as a patient."""
    page.goto(f"{BASE}/login")
    page.fill('input[type="email"], input[name="email"]', "patient@test.com")
    page.fill('input[type="password"], input[name="password"]', "Patient123!")
    page.click('button[type="submit"], button:has-text("Login")')
    page.wait_for_url(f"{BASE}/dashboard**", timeout=10_000)
    return page


# ─── TC-HP-001 ────────────────────────────────────────────────────────────────

def test_hp001_login_redirects_to_dashboard(page: Page):
    """Successful login redirects to dashboard."""
    page.goto(f"{BASE}/login")
    page.fill('input[type="email"], input[name="email"]', "patient@test.com")
    page.fill('input[type="password"], input[name="password"]', "Patient123!")
    page.click('button[type="submit"], button:has-text("Login")')
    page.wait_for_url(f"{BASE}/dashboard**", timeout=10_000)
    expect(page).to_have_url(f"{BASE}/dashboard")


# ─── TC-HP-002 ────────────────────────────────────────────────────────────────

def test_hp002_registration_form_validation(page: Page):
    """Empty registration form shows validation errors."""
    page.goto(f"{BASE}/register")
    page.click('button[type="submit"], button:has-text("Register")')

    # At least one error message should appear
    errors = page.locator(".error, .invalid-feedback, [role='alert']")
    expect(errors.first).to_be_visible()


# ─── TC-HP-004 ────────────────────────────────────────────────────────────────

def test_hp004_appointment_page_loads(logged_in_page: Page):
    """Appointment booking page is reachable after login."""
    page = logged_in_page
    page.click('a:has-text("Appointment"), a:has-text("Book"), nav >> text=Appointment')
    expect(page).not_to_have_url(f"{BASE}/login")


# ─── TC-HP-007 ────────────────────────────────────────────────────────────────

def test_hp007_logout_redirects_to_login(logged_in_page: Page):
    """Logout redirects to login and prevents back-navigation to protected pages."""
    page = logged_in_page
    page.click('button:has-text("Logout"), a:has-text("Logout")')
    page.wait_for_url(f"{BASE}/login**", timeout=8_000)
    expect(page).to_have_url(f"{BASE}/login")

    # Back button should not expose protected content
    page.go_back()
    # Should still be on login or redirected back
    assert "/login" in page.url or page.url == f"{BASE}/"


# ─── TC-EC-001 ────────────────────────────────────────────────────────────────

def test_ec001_invalid_login_shows_error(page: Page):
    """Invalid credentials show error without revealing which field is wrong."""
    page.goto(f"{BASE}/login")
    page.fill('input[type="email"], input[name="email"]', "ghost@nobody.com")
    page.fill('input[type="password"], input[name="password"]', "wrongpass")
    page.click('button[type="submit"], button:has-text("Login")')

    error = page.locator(".error, .alert-danger, [role='alert']")
    expect(error.first).to_be_visible(timeout=5_000)

    # Should NOT say "email not found" — that's user enumeration
    content = error.first.inner_text().lower()
    assert "not found" not in content
    assert "does not exist" not in content


# ─── TC-EC-005 ────────────────────────────────────────────────────────────────

def test_ec005_xss_not_executed(logged_in_page: Page):
    """XSS payload in profile name is not executed."""
    page = logged_in_page

    # Watch for any dialog (alert) that would indicate XSS
    dialog_fired = []
    page.on("dialog", lambda d: (dialog_fired.append(d.message), d.dismiss()))

    # Try to update profile with XSS payload
    page.goto(f"{BASE}/profile")
    name_input = page.locator('input[name="name"], input[placeholder*="name" i]')
    if name_input.count() > 0:
        name_input.fill("<script>alert('XSS')</script>")
        page.click('button[type="submit"], button:has-text("Save")')
        page.wait_for_timeout(2000)

    assert len(dialog_fired) == 0, f"XSS executed! Alert fired with: {dialog_fired}"
