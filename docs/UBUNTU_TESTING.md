# Ubuntu Frappe Bench Deployment & Testing Guide

This guide provides the exact commands and testing procedures to execute after pulling or moving the updated **WellPro** application into your Ubuntu Frappe Bench environment.

---

## 1. Environment Details (Discovered from Repository)

- **Bench Path**: `~/frappe/frappe-bench`
- **Frappe App Name**: `well_pro`
- **Site Name**: `well-pro`
- **Python Package / Module**: `well_pro` / `Well_pro_app`
- **Bench Python Virtualenv**: `~/frappe/frappe-bench/env/bin/python`

---

## 2. Step-by-Step Deployment Commands

Run the following commands in your Ubuntu terminal:

```bash
# 1. Navigate to the Frappe Bench directory
cd ~/frappe/frappe-bench

# 2. Synchronize DocTypes, schema changes, and indexes into MariaDB
bench --site well-pro migrate

# 3. Clear cached DocTypes and bytecode
bench --site well-pro clear-cache

# 4. Restart Bench services (Redis, gunicorn, background workers)
bench restart
```

---

## 3. Database Seeding (Test Users & 30-Day Historical Data)

A dedicated development seed script has been created to populate **User A** (30 days of continuous data and scores), **User B** (edge cases and missing data), and **Financial Categories**.

Run:
```bash
bench --site well-pro execute well_pro.well_pro_app.seed.seed_development_data
```

### What This Generates:
- **Financial Categories**: Salary, Groceries, Rent, Utilities, Investments, Debt Payments, Transfers, etc.
- **User A (`user_a@wellpro.test` / `WellProPassword123!`)**:
  - Profile & Consent preferences
  - 2 Financial Snapshots
  - 20+ Financial Transactions (Incomes, Expenses, Investments, Debt)
  - 30 days of Health Daily Records (varying sleep, steps, hydration, nutrition)
  - 15 Health Activity workout logs
  - 15 Social Activity interaction logs
  - 25 Subjective Wellbeing Check-ins
  - 30 calculated `Wellbeing Daily Score` records (v1)
- **User B (`user_b@wellpro.test` / `WellProPassword123!`)**:
  - Edge cases: day with missing sleep, day with only health data, day with only social data, snapshot without income, high loneliness reflection.

---

## 4. Running Automated Tests

Run the full automated test suite using Bench:

```bash
bench --site well-pro run-tests --app well_pro
```

To run individual test files:
```bash
# Normalization unit tests (14 tests)
bench --site well-pro run-tests --module well_pro.well_pro_app.tests.test_normalization

# Aggregation and trend unit tests
bench --site well-pro run-tests --module well_pro.well_pro_app.tests.test_aggregation

# Scoring engine mock tests
bench --site well-pro run-tests --module well_pro.well_pro_app.tests.test_scoring_engine

# Security, Multi-User Isolation & API integration tests
bench --site well-pro run-tests --module well_pro.well_pro_app.tests.test_security_and_api
```

---

## 5. Interactive Testing in `bench console`

You can verify Python imports, scoring logic, and database records interactively:

```bash
bench --site well-pro console
```

Inside the IPython console:

```python
import frappe
from well_pro.well_pro_app.services.scoring import calculate_daily_score, get_user_dashboard

# 1. Verify User A exists and has scores
scores = frappe.get_all("Wellbeing Daily Score", filters={"user": "user_a@wellpro.test"}, fields=["score_date", "overall_score", "health_score", "financial_score", "social_score"])
print(f"Total scores found for User A: {len(scores)}")
for s in scores[:5]:
    print(s)

# 2. Test dynamic calculation for a specific date
res = calculate_daily_score("user_a@wellpro.test", "2026-10-23")
print("Recalculated Score:", res)

# 3. Test full multi-dimensional dashboard structure
dashboard = get_user_dashboard("user_a@wellpro.test", "2026-10-23")
print("Health 30-Day Score:", dashboard["health"]["thirty_day_score"])
print("Health Trend:", dashboard["health"]["trend"], dashboard["health"]["trend_change"])
print("Overall Score:", dashboard["overall"]["score"])
```

---

## 6. End-to-End API Testing with `curl`

### 6.1 User Login
```bash
curl -X POST "http://localhost:8000/api/method/well_pro.well_pro_app.api.login"   -H "Content-Type: application/json"   -d '{"usr": "user_a@wellpro.test", "pwd": "WellProPassword123!"}'
```
*Take note of the returned `api_key` and `api_secret`.*

---

### 6.2 Fetch Dashboard Metrics
```bash
curl -G "http://localhost:8000/api/method/well_pro.well_pro_app.api.get_dashboard"   -H "Authorization: token <API_KEY>:<API_SECRET>"
```

---

### 6.3 Insert New Daily Health Record
```bash
curl -X POST "http://localhost:8000/api/method/well_pro.well_pro_app.api.insert_record"   -H "Authorization: token <API_KEY>:<API_SECRET>"   -H "Content-Type: application/json"   -d '{
    "doctype": "Health Daily Record",
    "record_data": {
      "record_date": "2026-10-23",
      "sleep_hours": 8.0,
      "sleep_quality": 5,
      "steps": 11000,
      "water_liters": 2.8,
      "energy_level": 4,
      "self_rated_health": 5
    }
  }'
```

---

### 6.4 Security Test: Multi-User Isolation
Attempt to access User B's data using User A's credentials:

```bash
# 1. Attempt to pass User B's email on insert
# Expected result: user field is overridden by server to user_a@wellpro.test
curl -X POST "http://localhost:8000/api/method/well_pro.well_pro_app.api.insert_record"   -H "Authorization: token <USER_A_KEY>:<USER_A_SECRET>"   -H "Content-Type: application/json"   -d '{
    "doctype": "Health Daily Record",
    "record_data": {
      "user": "user_b@wellpro.test",
      "record_date": "2026-10-22",
      "sleep_hours": 7.0
    }
  }'

# 2. Attempt to update User B's record
# Expected result: HTTP 403 PermissionError ("Permission denied: You do not own this record")
curl -X POST "http://localhost:8000/api/method/well_pro.well_pro_app.api.update_record"   -H "Authorization: token <USER_A_KEY>:<USER_A_SECRET>"   -H "Content-Type: application/json"   -d '{
    "doctype": "Health Daily Record",
    "name": "<USER_B_RECORD_NAME>",
    "update_data": {"sleep_hours": 10.0}
  }'

# 3. Attempt to insert arbitrary DocType ("User" or "System Settings")
# Expected result: HTTP 403 PermissionError ("DocType not permitted in WellPro API")
curl -X POST "http://localhost:8000/api/method/well_pro.well_pro_app.api.insert_record"   -H "Authorization: token <USER_A_KEY>:<USER_A_SECRET>"   -H "Content-Type: application/json"   -d '{
    "doctype": "User",
    "record_data": {"email": "hacked@example.com"}
  }'
```

---

## 7. Inspecting Logs & Debugging

If any issues occur:
```bash
# View recent Frappe error logs
bench --site well-pro show-error-log

# Check gunicorn / worker logs
tail -f ~/frappe/frappe-bench/logs/web.error.log
tail -f ~/frappe/frappe-bench/logs/worker.error.log
```

---

## 8. Summary of Environments & Checks Performed

| Check Type | Windows / Antigravity | Ubuntu / Frappe Bench |
| :--- | :---: | :---: |
| Python Syntax Compilation (`py_compile`) | **Completed & Passed** | Ready |
| DocType JSON Schema Validation | **Completed & Passed** | Applied on `bench migrate` |
| JSON Request Payloads Validation | **Completed & Passed** | Ready for curl / Postman |
| Math & Normalization Unit Tests (14 tests) | **Executed & Passed** | Ready |
| Exponential Recency Decay Tests | **Executed & Passed** | Ready |
| Scoring Engine Mock Tests (9 tests) | **Executed & Passed** | Ready |
| Frappe DB / MariaDB Migration | *Bench not installed* | Execute `bench migrate` |
| Integration Tests with MariaDB | *MariaDB not running* | Execute `bench run-tests` |
| Multi-process gunicorn server | *Not applicable* | Execute `bench restart` |
