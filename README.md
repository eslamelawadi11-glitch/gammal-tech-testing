# Gammal Tech — Healthcare App Test Suite
 
White-box / grey-box test plan and automation scripts for the simulated Gammal Tech healthcare web application (`https://gammal-tech-frontend.vercel.app/`).
 
---
 
## Structure
 
```
gammal-tech-testing/
├── TEST_PLAN.md          ← Full test plan (27 test cases)
├── locustfile.py         ← Stress / load tests (Locust)
├── tests/
│   ├── test_api.py       ← pytest API tests (TC-HP, TC-EC, TC-ST)
│   └── test_e2e.py       ← Playwright E2E browser tests
├── requirements.txt
└── README.md
```
 
---
 
## Test Coverage
 
| Category | Count |
|---|---|
| Happy Path | 8 |
| Edge Case | 14 |
| Stress / Load | 5 |
| **Total** | **27** |
 
---
 
## Quick Start
 
### 1. Install dependencies
 
```bash
pip install -r requirements.txt
playwright install chromium
```
 
### 2. Run API tests (pytest)
 
```bash
pytest tests/test_api.py -v
```
 
### 3. Run E2E tests (Playwright)
 
```bash
pytest tests/test_e2e.py -v --headed
```
 
### 4. Run Stress tests (Locust)
 
```bash
locust -f locustfile.py \
  --host=https://gammal-tech-frontend.vercel.app \
  --users 200 \
  --spawn-rate 20 \
  --run-time 5m \
  --headless
```
 
---
 
## Risk Areas (from Prior Security Audit)
 
1. Auth bypass via localStorage JWT storage
2. IDOR on patient records (object-level auth)
3. No rate limiting on login endpoint
4. Weak password policy not enforced server-side
5. Role privilege escalation via JWT tampering
---
 
## Author
 
Eslam Elawadi — [GitHub](https://github.com/eslamelawadi11-glitch)
