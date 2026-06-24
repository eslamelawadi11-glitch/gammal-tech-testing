# Test Plan — Gammal Tech Healthcare Web Application
**Version:** 1.0  
**Date:** 2026-06-24  
**Tester:** Eslam Elawadi  
**Target:** https://gammal-tech-frontend.vercel.app/  
**Classification:** White-Box / Grey-Box  
**Repository:** https://github.com/eslamelawadi11-glitch/gammal-tech-testing
 
---
 
## 1. Introduction
 
This test plan covers functional, security, edge-case, and stress testing for the simulated Gammal Tech healthcare web application. The application allows patients and healthcare staff to register, log in, manage appointments, and access patient records. Testing was informed by a prior white-box security audit that identified 9 vulnerabilities (Critical → Low).
 
---
 
## 2. Scope
 
| Area | In Scope |
|---|---|
| Authentication (Login / Register / Logout) | ✅ |
| Session & Token Management | ✅ |
| Patient Record CRUD | ✅ |
| Appointment Booking | ✅ |
| Role-Based Access Control (RBAC) | ✅ |
| Input Validation (client & server) | ✅ |
| API Endpoints | ✅ |
| Performance / Load Behaviour | ✅ |
| XSS / Injection Attack Surface | ✅ |
 
---
 
## 3. Test Environments
 
| Environment | URL / Notes |
|---|---|
| Production Mirror | https://gammal-tech-frontend.vercel.app/ |
| Backend API | As configured in the app (inspect network tab) |
| Browsers | Chrome 125+, Firefox 126+, Safari 17+ |
| Tools | Playwright, pytest, Locust, Burp Suite Community |
 
---
 
## 4. Roles Under Test
 
| Role | Credentials |
|---|---|
| Admin | admin@test.com / Admin123! |
| Doctor | doctor@test.com / Doctor123! |
| Patient | patient@test.com / Patient123! |
| Unauthenticated | — |
 
---
 
## 5. Test Cases
 
### 5.1 Happy Path Tests (Everything Works)
 
---
 
#### TC-HP-001 — Successful Login (Patient)
**Category:** Happy Path  
**Priority:** P0  
**Module:** Authentication  
 
**Preconditions:** Valid patient account exists.
 
**Steps:**
1. Navigate to `/login`.
2. Enter valid email and password.
3. Click "Login".
**Expected Result:** Redirected to the patient dashboard. Session token stored. No error shown.
 
**Pass Criteria:** HTTP 200, dashboard renders, user name visible.
 
---
 
#### TC-HP-002 — Successful Registration (New Patient)
**Category:** Happy Path  
**Priority:** P0  
**Module:** Authentication  
 
**Preconditions:** Email not previously registered.
 
**Steps:**
1. Navigate to `/register`.
2. Fill all required fields with valid data (name, email, password, age, gender).
3. Click "Register".
**Expected Result:** Account created. Redirected to dashboard or login page with success message.
 
**Pass Criteria:** HTTP 201 from API, user record created in DB, no sensitive data in response body.
 
---
 
#### TC-HP-003 — View Own Patient Record
**Category:** Happy Path  
**Priority:** P0  
**Module:** Patient Records  
 
**Preconditions:** Logged in as patient with existing record.
 
**Steps:**
1. Log in as patient.
2. Navigate to "My Records" / profile section.
**Expected Result:** Patient's own medical history, diagnoses, and prescriptions display correctly.
 
**Pass Criteria:** Data matches seeded record. No other patient's data visible.
 
---
 
#### TC-HP-004 — Book an Appointment
**Category:** Happy Path  
**Priority:** P0  
**Module:** Appointments  
 
**Preconditions:** Logged in as patient, at least one doctor available.
 
**Steps:**
1. Navigate to "Book Appointment".
2. Select a doctor, date, and time slot.
3. Confirm booking.
**Expected Result:** Appointment created. Confirmation shown. Appointment appears in patient's upcoming list.
 
**Pass Criteria:** HTTP 201, appointment visible in dashboard, no duplicate booking created.
 
---
 
#### TC-HP-005 — Doctor Views Patient Record
**Category:** Happy Path  
**Priority:** P1  
**Module:** Patient Records / RBAC  
 
**Preconditions:** Logged in as doctor. Patient has an appointment with this doctor.
 
**Steps:**
1. Log in as doctor.
2. Open patient list or appointment.
3. Click on patient to view record.
**Expected Result:** Patient's record loads. Doctor can view but not modify (unless system allows).
 
**Pass Criteria:** Record renders, no authorization error for legitimate doctor-patient relationship.
 
---
 
#### TC-HP-006 — Admin Manages Users
**Category:** Happy Path  
**Priority:** P1  
**Module:** Admin / RBAC  
 
**Preconditions:** Logged in as admin.
 
**Steps:**
1. Navigate to admin panel.
2. View user list.
3. Change a user's role from Patient to Doctor.
4. Save changes.
**Expected Result:** Role updated. User now has doctor-level access on next login.
 
**Pass Criteria:** HTTP 200, DB role reflects change, audit log entry created (if applicable).
 
---
 
#### TC-HP-007 — Logout Terminates Session
**Category:** Happy Path  
**Priority:** P0  
**Module:** Authentication  
 
**Preconditions:** Logged in as any user.
 
**Steps:**
1. Click Logout.
2. Attempt to navigate to a protected route (e.g., `/dashboard`).
**Expected Result:** Redirected to login page. Previous session token rejected.
 
**Pass Criteria:** Token removed from storage, protected API calls return 401, no cached data exposed.
 
---
 
#### TC-HP-008 — Cancel an Appointment
**Category:** Happy Path  
**Priority:** P1  
**Module:** Appointments  
 
**Preconditions:** Patient has an upcoming appointment.
 
**Steps:**
1. Navigate to appointment list.
2. Click "Cancel" on an upcoming appointment.
3. Confirm cancellation.
**Expected Result:** Appointment status changes to "Cancelled". Slot freed up.
 
**Pass Criteria:** HTTP 200, appointment no longer shows as "Upcoming".
 
---
 
### 5.2 Edge Case Tests (Unexpected Inputs)
 
---
 
#### TC-EC-001 — Login with Unregistered Email
**Category:** Edge Case  
**Priority:** P1  
**Module:** Authentication  
 
**Steps:**
1. Enter a non-existent email and any password.
2. Click Login.
**Expected Result:** Error message: "Invalid credentials." No user enumeration (same message as wrong password).
 
**Pass Criteria:** HTTP 401, response body does NOT differentiate "email not found" from "wrong password". No stack trace.
 
---
 
#### TC-EC-002 — Register with Already-Used Email
**Category:** Edge Case  
**Priority:** P1  
**Module:** Authentication  
 
**Steps:**
1. Attempt to register with an email that already exists.
**Expected Result:** Error: "Email already in use." Form resets or highlights email field.
 
**Pass Criteria:** HTTP 409. No duplicate record in DB. Response does not confirm account details.
 
---
 
#### TC-EC-003 — Weak Password on Registration
**Category:** Edge Case  
**Priority:** P1  
**Module:** Input Validation  
 
**Steps:**
1. Register with password: `123`, `password`, `aaaaaa`.
**Expected Result:** Validation error listing password requirements (min length, complexity).
 
**Pass Criteria:** Registration blocked client-side AND server-side. HTTP 400. Weak password not stored.
 
---
 
#### TC-EC-004 — SQL Injection in Login Fields
**Category:** Edge Case / Security  
**Priority:** P0  
**Module:** Authentication / Security  
 
**Payloads:**
```
' OR '1'='1
' OR 1=1--
admin'--
" OR ""="
```
 
**Steps:**
1. Enter each payload in the email and/or password field.
2. Click Login.
**Expected Result:** Login fails. No database error exposed. No unauthorized access.
 
**Pass Criteria:** HTTP 401 or 400. Response body contains no SQL error messages. Application remains stable.
 
---
 
#### TC-EC-005 — XSS in Patient Name / Notes Field
**Category:** Edge Case / Security  
**Priority:** P0  
**Module:** Patient Records / Security  
 
**Payloads:**
```html
<script>alert('XSS')</script>
<img src=x onerror=alert(1)>
javascript:alert(1)
"><svg/onload=alert(1)>
```
 
**Steps:**
1. Log in as patient or admin.
2. Update a text field (name, notes, diagnosis) with each payload.
3. Save. Navigate away and back to the record.
**Expected Result:** Payload rendered as plain text (escaped). No JavaScript execution.
 
**Pass Criteria:** `alert()` never fires. Payload stored as `&lt;script&gt;` in source. Content-Security-Policy header blocks inline scripts.
 
---
 
#### TC-EC-006 — Access Another Patient's Record (IDOR)
**Category:** Edge Case / Security  
**Priority:** P0  
**Module:** Patient Records / RBAC  
 
**Steps:**
1. Log in as Patient A. Note your patient ID in the URL (e.g., `/patients/42`).
2. Manually change the ID to another patient's (e.g., `/patients/43`).
**Expected Result:** HTTP 403 Forbidden. Patient A cannot view Patient B's record.
 
**Pass Criteria:** Server validates ownership / role on every request. No record data in 403 response.
 
---
 
#### TC-EC-007 — Book Appointment on a Past Date
**Category:** Edge Case  
**Priority:** P2  
**Module:** Appointments  
 
**Steps:**
1. Attempt to book an appointment with a date in the past (e.g., 2020-01-01).
**Expected Result:** Validation error: "Cannot book past appointments."
 
**Pass Criteria:** Client AND server reject the date. No appointment created.
 
---
 
#### TC-EC-008 — Duplicate Appointment Booking
**Category:** Edge Case  
**Priority:** P1  
**Module:** Appointments  
 
**Steps:**
1. Book Appointment A for Doctor X, date Y, time Z.
2. Attempt to book the same slot again.
**Expected Result:** Error: "Slot already booked." or "You already have an appointment at this time."
 
**Pass Criteria:** HTTP 409. Database has exactly one record for that slot.
 
---
 
#### TC-EC-009 — Empty / Missing Required Fields on Registration
**Category:** Edge Case  
**Priority:** P1  
**Module:** Input Validation  
 
**Steps:**
1. Submit registration form with empty name, email, and/or password.
**Expected Result:** Field-level validation errors appear. Form not submitted.
 
**Pass Criteria:** HTTP 400. Each missing field has a meaningful error message. No partial record saved.
 
---
 
#### TC-EC-010 — Extremely Long Input in Text Fields
**Category:** Edge Case  
**Priority:** P2  
**Module:** Input Validation  
 
**Steps:**
1. Enter a 10,000-character string in name, notes, or address fields.
2. Submit.
**Expected Result:** Field length validation triggers. Input truncated or rejected.
 
**Pass Criteria:** No server crash (HTTP 500). No database overflow error exposed. Response is graceful.
 
---
 
#### TC-EC-011 — JWT / Session Token Tampering
**Category:** Edge Case / Security  
**Priority:** P0  
**Module:** Authentication / Security  
 
**Steps:**
1. Log in and copy the JWT from localStorage.
2. Decode the token (base64). Change `"role": "patient"` to `"role": "admin"`.
3. Re-encode and replace the token in localStorage.
4. Navigate to an admin-only route.
**Expected Result:** Server rejects tampered token. HTTP 401 or 403. Access denied.
 
**Pass Criteria:** Server validates JWT signature on every request. Tampered token signature fails validation.
 
---
 
#### TC-EC-012 — Direct API Access Without Token
**Category:** Edge Case / Security  
**Priority:** P0  
**Module:** API Security  
 
**Steps:**
1. Using curl or Postman, call a protected endpoint (e.g., `GET /api/patients`) with no Authorization header.
**Expected Result:** HTTP 401 Unauthorized. No data returned.
 
**Pass Criteria:** Every protected endpoint requires a valid token. No endpoint accidentally left open.
 
---
 
#### TC-EC-013 — Upload Invalid File Type (if file upload exists)
**Category:** Edge Case  
**Priority:** P2  
**Module:** File Upload / Input Validation  
 
**Steps:**
1. Attempt to upload a `.exe`, `.php`, or `.js` file as a profile photo or medical document.
**Expected Result:** File type rejected. Error message shown. File not stored.
 
**Pass Criteria:** Server validates MIME type and extension. No executable file stored on server.
 
---
 
#### TC-EC-014 — Concurrent Booking of Same Slot (Race Condition)
**Category:** Edge Case  
**Priority:** P1  
**Module:** Appointments / Concurrency  
 
**Steps:**
1. Open two browser sessions as two different patients.
2. Both navigate to the same doctor + same time slot.
3. Both click "Book" at nearly the same time.
**Expected Result:** Only one booking succeeds. The other receives a conflict error.
 
**Pass Criteria:** Database has exactly one appointment for that slot. No ghost bookings. Race condition handled (DB-level lock or transaction).
 
---
 
### 5.3 Stress Tests (What Breaks Under Load)
 
---
 
#### TC-ST-001 — Login Endpoint Under Sustained Load
**Category:** Stress Test  
**Priority:** P1  
**Module:** Authentication  
 
**Tool:** Locust / k6
 
**Configuration:**
```
Users: 200 concurrent
Ramp-up: 30 seconds
Duration: 5 minutes
Endpoint: POST /api/auth/login
```
 
**Expected Result:** Response time < 2 seconds at P95. Error rate < 1%. No HTTP 500s.
 
**Pass Criteria:**  
- P95 latency ≤ 2000ms  
- Error rate ≤ 1%  
- Application remains stable after test ends  
---
 
#### TC-ST-002 — Patient Records List Under Load
**Category:** Stress Test  
**Priority:** P1  
**Module:** Patient Records  
 
**Configuration:**
```
Users: 100 concurrent doctors/admins
Ramp-up: 20 seconds
Duration: 3 minutes
Endpoint: GET /api/patients
```
 
**Expected Result:** All responses return correct data. No partial records or mixing of patient data.
 
**Pass Criteria:**  
- Response integrity maintained  
- No data leakage between user sessions  
- P99 latency ≤ 5000ms  
---
 
#### TC-ST-003 — Brute Force Protection on Login
**Category:** Stress Test / Security  
**Priority:** P0  
**Module:** Authentication / Rate Limiting  
 
**Steps:**
1. Send 50 rapid login attempts with wrong passwords for the same account.
**Expected Result:** After N failed attempts (typically 5–10), account is locked or rate-limited. HTTP 429 or 423.
 
**Pass Criteria:**  
- Rate limiting kicks in within 10 attempts  
- Lockout message shown to user  
- Legitimate login restores after cooldown / unlock flow  
---
 
#### TC-ST-004 — Appointment Booking Spike (Flash Load)
**Category:** Stress Test  
**Priority:** P2  
**Module:** Appointments  
 
**Configuration:**
```
Users: 500 concurrent
Ramp-up: 5 seconds (sudden spike)
Duration: 1 minute
Endpoint: POST /api/appointments
```
 
**Expected Result:** System queues or rejects excess requests gracefully. No data corruption. Booked appointments are accurate.
 
**Pass Criteria:**  
- HTTP 503 or 429 returned (not 500) for rejected requests  
- Successfully booked records remain intact  
- No duplicate bookings created under spike  
---
 
#### TC-ST-005 — API Sustained Traffic (Soak Test)
**Category:** Stress Test  
**Priority:** P2  
**Module:** Full Application  
 
**Configuration:**
```
Users: 50 concurrent (moderate load)
Duration: 60 minutes
Endpoints: Mixed (login, view records, book appointment)
```
 
**Expected Result:** Memory usage stable. No memory leaks. Response times consistent throughout.
 
**Pass Criteria:**  
- Response time does not degrade > 20% from minute 5 to minute 60  
- Server does not crash or restart  
- No gradual increase in error rate  
---
 
## 6. Test Execution Summary Template
 
| TC ID | Module | Category | Priority | Result | Notes |
|---|---|---|---|---|---|
| TC-HP-001 | Auth | Happy Path | P0 | | |
| TC-HP-002 | Auth | Happy Path | P0 | | |
| TC-HP-003 | Records | Happy Path | P0 | | |
| TC-HP-004 | Appointments | Happy Path | P0 | | |
| TC-HP-005 | Records/RBAC | Happy Path | P1 | | |
| TC-HP-006 | Admin/RBAC | Happy Path | P1 | | |
| TC-HP-007 | Auth | Happy Path | P0 | | |
| TC-HP-008 | Appointments | Happy Path | P1 | | |
| TC-EC-001 | Auth | Edge Case | P1 | | |
| TC-EC-002 | Auth | Edge Case | P1 | | |
| TC-EC-003 | Validation | Edge Case | P1 | | |
| TC-EC-004 | Security | Edge Case | P0 | | |
| TC-EC-005 | Security | Edge Case | P0 | | |
| TC-EC-006 | Security | Edge Case | P0 | | |
| TC-EC-007 | Appointments | Edge Case | P2 | | |
| TC-EC-008 | Appointments | Edge Case | P1 | | |
| TC-EC-009 | Validation | Edge Case | P1 | | |
| TC-EC-010 | Validation | Edge Case | P2 | | |
| TC-EC-011 | Security | Edge Case | P0 | | |
| TC-EC-012 | Security | Edge Case | P0 | | |
| TC-EC-013 | File Upload | Edge Case | P2 | | |
| TC-EC-014 | Concurrency | Edge Case | P1 | | |
| TC-ST-001 | Auth | Stress | P1 | | |
| TC-ST-002 | Records | Stress | P1 | | |
| TC-ST-003 | Security | Stress | P0 | | |
| TC-ST-004 | Appointments | Stress | P2 | | |
| TC-ST-005 | Full App | Stress | P2 | | |
 
**Total: 27 test cases** (8 Happy Path, 14 Edge Case, 5 Stress)
 
---
 
## 7. Priority Definitions
 
| Priority | Meaning |
|---|---|
| P0 | Critical — blocks release if failed |
| P1 | High — must fix before release |
| P2 | Medium — fix in next sprint |
| P3 | Low — nice to have |
 
---
 
## 8. Entry & Exit Criteria
 
**Entry:**
- Application deployed and accessible at target URL
- Test accounts provisioned
- Postman collection / test scripts ready
**Exit:**
- All P0 test cases pass
- No open P0 bugs
- P1 pass rate ≥ 90%
- Stress test results documented
---
 
## 9. Known Risk Areas (from Prior Security Audit)
 
Based on the white-box audit conducted previously, the following areas carry elevated risk and deserve focused testing:
 
1. **Authentication bypass via localStorage** — JWT stored in localStorage; XSS can steal it. Validate CSP headers and HttpOnly flags.
2. **IDOR on patient records** — Object-level authorization must be verified on every API endpoint.
3. **No rate limiting on login** — Brute force path is open; TC-ST-003 directly validates this fix.
4. **Weak password policy** — TC-EC-003 validates enforcement.
5. **Role privilege escalation** — TC-EC-011 validates server-side JWT validation.
---
 
## 10. Tools & Automation
 
| Tool | Use |
|---|---|
| Playwright | E2E happy path and edge case automation |
| pytest | Unit / integration tests for API |
| Locust | Load and stress testing |
| Burp Suite Community | Manual security testing (SQLi, XSS, IDOR) |
| Postman | API collection for manual and automated API tests |
