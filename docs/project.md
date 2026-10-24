# WellPro / Well_pro_app Comprehensive Project Documentation

---

## 1. Executive Project Summary

**WellPro** (`well_pro` / `Well_pro_app`) is a backend web application built on the **Frappe Framework** (v14/v15) designed to track, analyze, and score personal holistic wellbeing across three primary pillars:
1. **Physical Health**: Sleep duration/quality, physical exercise, daily step counts, hydration, nutrition (calories, protein, fruit/vegetable servings), and daily energy levels.
2. **Financial Wellbeing**: Savings behavior, expense-to-income management, debt burden ratio, emergency fund reserve coverage, and subjective financial stress.
3. **Social Wellbeing**: Real-life interaction quality, relational connection depth, social satisfaction, loneliness mitigation, and post-interaction mood impact.
4. **Subjective Daily Check-Ins**: Evening reflection capturing emotional state, daily vitality, stress, and fulfillment.

The platform provides a **backend scoring engine** that ingests raw multi-source data (manual entry, voice transcripts, OCR receipts, and wearable integrations), normalizes each metric to a bounded `0.0 – 100.0` scale, handles incomplete data via weight renormalization, stores daily scores idempotently, and computes 7-day, 30-day, and 90-day exponential recency-weighted period scores and trend vectors.

---

## 2. Complete Folder & File Tree

```
well_pro/
├── LICENSE
├── README.md
├── license.txt
├── pyproject.toml                         # Project package metadata & ruff config
├── docs/                                  # Comprehensive documentation
│   ├── API.md                             # REST API specification & curl guide
│   ├── CODE_REVIEW.md                     # Architecture audit & code review report
│   ├── SCORING.md                         # Mathematical scoring specification
│   ├── UBUNTU_TESTING.md                  # Ubuntu bench deployment & execution runbook
│   ├── doctype.md                         # DocType schemas & AI agent tool calling guide
│   └── project.md                         # Complete project & code explanation (this file)
├── testing/                               # API Test Payloads
│   └── json/                              # 22 Standalone JSON test payloads
│       ├── 01_signup_user.json
│       ├── 02_login_user.json
│       ├── 03_create_health_daily_record.json
│       ├── 04_create_health_activity.json
│       ├── 05_create_financial_transaction_income.json
│       ├── 06_create_financial_transaction_expense.json
│       ├── 07_create_financial_snapshot.json
│       ├── 08_create_social_activity.json
│       ├── 09_create_subjective_wellbeing_checkin.json
│       ├── 10_update_health_record.json
│       ├── 11_recalculate_score.json
│       ├── 12_store_ai_record_health.json
│       ├── 13_store_ai_record_financial.json
│       ├── 14_store_ai_record_social.json
│       ├── 15_delete_record.json
│       ├── duplicate_daily_record.json
│       ├── invalid_negative_amount.json
│       ├── invalid_rating_out_of_bounds.json
│       ├── invalid_score_direct_insertion.json
│       ├── mass_assignment_tampering.json
│       ├── unauthorized_doctype_injection.json
│       └── unauthorized_user_spoofing.json
└── well_pro/                              # Frappe App Root Package
    ├── __init__.py                        # Version declaration (0.0.1)
    ├── api.py                             # Top-level API compatibility proxy
    ├── hooks.py                           # Frappe app configuration & scheduler events
    ├── modules.txt                        # Modules list ("Well Pro", "Well_pro_app")
    ├── patches.txt                        # Database migration patches
    └── well_pro_app/                      # Primary Backend Module
        ├── __init__.py                    # Module init
        ├── api.py                         # Authenticated REST API & CRUD endpoints
        ├── hooks.py                       # Sub-module hooks reference
        ├── scoring.py                     # Backward-compatibility scoring proxy
        ├── tasks.py                       # Scheduled nightly scoring cron worker
        ├── seed.py                        # Development database seeding script
        ├── doctype/                       # 10 Frappe DocTypes
        │   ├── financial_category/
        │   │   ├── financial_category.json
        │   │   ├── financial_category.py
        │   │   └── financial_category.js
        │   ├── financial_snapshot/
        │   │   ├── financial_snapshot.json
        │   │   ├── financial_snapshot.py
        │   │   └── financial_snapshot.js
        │   ├── financial_transaction/
        │   │   ├── financial_transaction.json
        │   │   ├── financial_transaction.py
        │   │   └── financial_transaction.js
        │   ├── health_activity/
        │   │   ├── health_activity.json
        │   │   ├── health_activity.py
        │   │   └── health_activity.js
        │   ├── health_daily_record/
        │   │   ├── health_daily_record.json
        │   │   ├── health_daily_record.py
        │   │   └── health_daily_record.js
        │   ├── social_activity/
        │   │   ├── social_activity.json
        │   │   ├── social_activity.py
        │   │   └── social_activity.js
        │   ├── subjective_wellbeing_checkin/
        │   │   ├── subjective_wellbeing_checkin.json
        │   │   ├── subjective_wellbeing_checkin.py
        │   │   └── subjective_wellbeing_checkin.js
        │   ├── user_consent_preference/
        │   │   ├── user_consent_preference.json
        │   │   ├── user_consent_preference.py
        │   │   └── user_consent_preference.js
        │   ├── wellbeing_daily_score/
        │   │   ├── wellbeing_daily_score.json
        │   │   ├── wellbeing_daily_score.py
        │   │   └── wellbeing_daily_score.js
        │   └── wellpro_profile/
        │       ├── wellpro_profile.json
        │       ├── wellpro_profile.py
        │       └── wellpro_profile.js
        ├── services/                      # Modular Business Logic Services
        │   ├── __init__.py
        │   └── scoring/                   # Decoupled Scoring Engine
        │       ├── __init__.py            # Package exports
        │       ├── config.py              # Weights, parameters, thresholds
        │       ├── normalization.py       # Math normalizers (0-100)
        │       ├── health.py              # Health score & confidence calculator
        │       ├── financial.py           # Financial score & confidence calculator
        │       ├── social.py              # Social score & confidence calculator
        │       ├── aggregation.py         # Recency decay, trends & overall score
        │       └── service.py             # Daily score upsert & dashboard builder
        └── tests/                         # Automated Test Suite
            ├── __init__.py
            ├── test_normalization.py      # Normalization mathematical unit tests
            ├── test_aggregation.py        # Exponential decay & trend unit tests
            ├── test_scoring_engine.py     # Domain scoring tests with mocked db
            └── test_security_and_api.py   # Multi-user isolation & API integration tests
```

---

## 3. Deep Line-by-Line & Block-by-Block Code Walkthrough

---

### 3.1 App Hooks Configuration (`well_pro/hooks.py`)
`hooks.py` is the primary entry point read by the Frappe framework to register apps, scheduled events, and overrides.

```python
app_name = "well_pro"
app_title = "Well Pro"
app_publisher = "Ahmad"
app_description = "this is app to trach the health and other financial thing of a person . this frappe act as a backend "
app_email = "raiahmadnawaz.019@gmail.com"
app_license = "mit"
```
* **Explanation**: Declares app metadata for Frappe Desk, Apps screen, and package management.

```python
# Scheduled Tasks
# ---------------
scheduler_events = {
	"daily": [
		"well_pro.well_pro_app.tasks.run_nightly_wellbeing_scoring"
	]
}
```
* **Explanation**: Registers the background cron task that runs nightly across all registered users on the site to recalculate their daily wellbeing score.

---

### 3.2 Top-Level API Compatibility Layer (`well_pro/api.py`)
Acts as a transparent proxy to prevent breaking legacy frontend clients or external services calling `/api/method/well_pro.api.<method>`.

```python
import frappe
from well_pro.well_pro_app.api import (
    signup,
    login,
    verify_user_session,
    insert_record,
    store_ai_record,
    update_record,
    delete_record,
    get_user_records,
    get_dashboard,
    get_dashboard_metrics,
    recalculate_score,
    success_response,
    error_response
)

__all__ = [
    "signup", "login", "verify_user_session", "insert_record",
    "store_ai_record", "update_record", "delete_record",
    "get_user_records", "get_dashboard", "get_dashboard_metrics",
    "recalculate_score", "success_response", "error_response"
]
```
* **Explanation**: Imports all active API functions from `well_pro.well_pro_app.api` and exposes them in the `well_pro.api` module namespace.

---

### 3.3 Main API Controller (`well_pro/well_pro_app/api.py`)

#### Security Constants & Envelopes
```python
ALLOWED_DOCTYPES = {
    "Health Daily Record", "Health Activity", "Financial Transaction",
    "Financial Snapshot", "Financial Category", "Social Activity",
    "Subjective Wellbeing Checkin", "User Consent Preference",
    "WellPro Profile", "Wellbeing Daily Score"
}
```
* **Explanation**: An explicit allowlist that strictly restricts what DocTypes can be passed to generic CRUD endpoints. Any request containing an unlisted DocType (e.g. `User`, `Role`, `System Settings`) is immediately rejected.

```python
USER_OWNED_DOCTYPES = {
    "Health Daily Record", "Health Activity", "Financial Transaction",
    "Financial Snapshot", "Social Activity", "Subjective Wellbeing Checkin",
    "User Consent Preference", "WellPro Profile", "Wellbeing Daily Score"
}
```
* **Explanation**: Identifies DocTypes where documents belong to a specific user (`user` field). Used to enforce multi-user query filtering and ownership isolation.

```python
PROTECTED_FIELDS = {
    "name", "owner", "creation", "modified_by", "docstatus", "idx"
}
```
* **Explanation**: System-controlled metadata fields stripped from client payloads on insert and update to prevent tampering and mass-assignment vulnerabilities.

```python
def success_response(data: Any = None, message: str = "Success", **kwargs) -> Dict[str, Any]:
    res = {
        "success": True,
        "message": message,
        "data": data
    }
    res.update(kwargs)
    return res

def error_response(message: str = "An error occurred", errors: Optional[Dict[str, Any]] = None, code: int = 400) -> Dict[str, Any]:
    frappe.response["http_status_code"] = code
    return {
        "success": False,
        "message": message,
        "errors": errors or {}
    }
```
* **Explanation**: Standardized JSON envelopes providing consistent responses across mobile, web, and AI agent clients.

```python
def _extract_affected_date(doc: Any) -> str:
    if hasattr(doc, "record_date") and doc.record_date:
        return str(doc.record_date)
    if hasattr(doc, "transaction_date") and doc.transaction_date:
        return str(doc.transaction_date)
    if hasattr(doc, "snapshot_date") and doc.snapshot_date:
        return str(doc.snapshot_date)
    if hasattr(doc, "date") and doc.date:
        return str(doc.date)
    if hasattr(doc, "score_date") and doc.score_date:
        return str(doc.score_date)
    if hasattr(doc, "logged_at") and doc.logged_at:
        return str(doc.logged_at).split()[0]
    return today()
```
* **Explanation**: Dynamically resolves the exact calendar date (`YYYY-MM-DD`) affected by a document insertion, update, or deletion. This ensures historical records (e.g. October 10) trigger recalculation for October 10 rather than blindly recalculating today.

#### Authentication Methods
```python
@frappe.whitelist(allow_guest=True)
def signup(email: str, password: str, first_name: str, last_name: Optional[str] = None):
```
* **Lines 98–156**:
  1. Validates email structure and password length ($\ge 6$ chars).
  2. Ensures the user does not already exist via `frappe.db.exists("User", email)`.
  3. Creates a standard user document (`user_type="System User"`, enabled). **Crucially does NOT grant `System Manager`**.
  4. Generates an API key and API secret pair for token authentication.
  5. Automatically creates matching `WellPro Profile` and `User Consent Preference` documents.
  6. Commits transaction and returns API credentials.

```python
@frappe.whitelist(allow_guest=True)
def login(usr: str, pwd: str):
```
* **Lines 159–185**:
  1. Authenticates user credentials via Frappe's `LoginManager`.
  2. Ensures the user has an `api_key` and `api_secret` generated, creating them on first login if absent.
  3. Returns active token credentials for API access.

```python
@frappe.whitelist()
def verify_user_session():
```
* **Lines 188–205**:
  1. Verifies caller is authenticated (`user != "Guest"`).
  2. Fetches active user profile and consent settings from the database.

#### CRUD Operations & Score Invalidation
```python
@frappe.whitelist()
def insert_record(doctype: str, record_data: Any):
```
* **Lines 212–257**:
  1. Verifies session authentication.
  2. Runs `_validate_doctype(doctype)` against `ALLOWED_DOCTYPES`.
  3. Blocks direct insertion into `Wellbeing Daily Score` (only the scoring engine can write scores).
  4. Requires `System Manager` to create `Financial Category`.
  5. Forces `record_data["user"] = frappe.session.user` (overriding any client-supplied user).
  6. Strips `PROTECTED_FIELDS`.
  7. Inserts doc using Frappe ORM (`doc.insert(ignore_permissions=False)`).
  8. Calls `calculate_daily_score(user, affected_date)` to immediately refresh that date's score.

```python
@frappe.whitelist()
def store_ai_record(domain: str, record_data: Any):
```
* **Lines 260–298**:
  1. Validates `domain` against `DOMAIN_DOCTYPE_MAP` (`health`, `financial`, `health_activity`, `social`, `wellbeing`).
  2. Sets target DocType, forces caller user ownership, strips protected fields, and inserts.
  3. Triggers dynamic score recalculation for the extracted date.

```python
@frappe.whitelist()
def update_record(doctype: str, name: str, update_data: Any):
```
* **Lines 305–354**:
  1. Validates doctype against allowlist.
  2. Verifies record exists.
  3. **Multi-User Isolation Check**: Ensures `doc.user == frappe.session.user` unless caller has `System Manager` role.
  4. Strips `PROTECTED_FIELDS`, `user`, and `doctype` from `update_data` to prevent identity tampering.
  5. Tracks `old_date` and `new_date`. Updates and saves document.
  6. Recalculates scores for `old_date` and `new_date` (if the record was moved across dates).

```python
@frappe.whitelist()
def delete_record(doctype: str, name: str):
```
* **Lines 361–396**:
  1. Verifies doctype allowlist and caller ownership.
  2. Extracts affected date prior to deletion.
  3. Deletes document via `doc.delete()`.
  4. Recalculates score for that date so metrics immediately reflect the deletion.

```python
@frappe.whitelist()
def get_user_records(doctype: str, limit: int = 50, offset: int = 0, order_by: str = "modified desc", from_date: Optional[str] = None, to_date: Optional[str] = None):
```
* **Lines 403–452**:
  1. Validates doctype against allowlist.
  2. Automatically applies `filters = {"user": frappe.session.user}`.
  3. Applies date filters (`from_date`, `to_date`) to the appropriate date field of the doctype.
  4. Applies safe pagination (`limit_start=offset`, `limit_page_length=min(limit, 200)`).

#### Dashboard & Scoring APIs
```python
@frappe.whitelist(methods=["POST"])
def recalculate_score(date: Optional[str] = None, target_user: Optional[str] = None):
```
* **Lines 459–482**:
  1. Enforces caller identity: normal users can only recalculate their own scores. Only `System Manager` can pass another `target_user`.
  2. Executes `calculate_daily_score` for the target date and returns the updated scores.

```python
@frappe.whitelist(methods=["GET"])
def get_dashboard(as_of_date: Optional[str] = None):
```
* **Lines 485–500**:
  1. Calls `get_user_dashboard(user, as_of_date)`.
  2. Returns the multi-dimensional metrics object (Health, Financial, Social, and Overall scores across today, 7d, 30d, 90d, confidences, and trends).

---

### 3.4 Scheduled Background Tasks (`well_pro/well_pro_app/tasks.py`)
```python
import frappe
from frappe.utils import today
from well_pro.well_pro_app.services.scoring import calculate_daily_score

def run_nightly_wellbeing_scoring():
    """Background daily cron job calculating wellbeing scores for all active users."""
    users = frappe.get_all("User", filters={"enabled": 1, "user_type": "System User"}, fields=["name"])
    calc_date = today()
    for u in users:
        try:
            calculate_daily_score(u.name, calc_date)
        except Exception as e:
            frappe.log_error(
                f"Nightly scoring error for user {u.name} on {calc_date}: {str(e)}",
                "WellPro Nightly Scoring Failure"
            )
```
* **Explanation**: Iterates through all active system users and executes `calculate_daily_score(u.name, today())`. Errors for individual users are caught and logged to `tabError Log` without halting the entire background batch.

---

### 3.5 Scoring Service Modules (`well_pro/well_pro_app/services/scoring/`)

#### 1. Configuration (`config.py`)
Centralizes all algorithm constants, weights, and parameters so adjustments never require changing controller or normalizer code:
- `SCORING_VERSION = "v1"`
- `CATEGORY_WEIGHTS = {"health": 0.40, "financial": 0.35, "social": 0.25}`
- `HEALTH_METRIC_WEIGHTS`: Sleep (30%), Exercise (20%), Activity (15%), Nutrition (15%), Hydration (10%), Self-rated (10%).
- `FINANCIAL_METRIC_WEIGHTS`: Savings (30%), Expense/Budget (25%), Debt (20%), Emergency Fund (15%), Financial Stress (10%).
- `SOCIAL_METRIC_WEIGHTS`: Quality (25%), Connection (25%), Satisfaction (20%), Loneliness (15%), Mood (15%).
- `HALF_LIFE_DAYS = 14.0`, $\lambda = \ln(2)/14 \approx 0.04951$.
- `TREND_IMPROVING_THRESHOLD = 5.0`, `TREND_DECLINING_THRESHOLD = -5.0`.

#### 2. Normalization Engine (`normalization.py`)
Contains pure mathematical functions that take raw values and return `float` scores bounded strictly to `0.0 – 100.0`:
- `clamp(val, min_val=0.0, max_val=100.0)`: Bounds numeric output.
- `normalize_rating(rating, min_rating=1, max_rating=5)`: Scales subjective ratings $1\rightarrow 0$, $2\rightarrow 25$, $3\rightarrow 50$, $4\rightarrow 75$, $5\rightarrow 100$.
- `normalize_inverse_rating(rating)`: Scales negative factors (stress/loneliness) $1\rightarrow 100$, $5\rightarrow 0$.
- `normalize_higher_is_better(val, target)`: Computes progress towards target $\min(val/target, 1.0) \times 100$.
- `normalize_lower_is_better(val, good, bad)`: High score for values $\le good$, decaying to 0 for $\ge bad$.
- `normalize_target_range(val, opt_min, opt_max, tol_min, tol_max)`: Plateau of 100 inside optimal range, decaying linearly to 0 at tolerance boundaries.

#### 3. Domain Calculators (`health.py`, `financial.py`, `social.py`)
Each module queries the database for user source records on the target date:
- For every metric with data present, computes the metric score and registers its expected weight.
- Missing metrics are excluded from the score denominator.
- Renormalizes weights:
  $$\text{score} = \frac{\sum (\text{metric\_score} \times \text{metric\_weight})}{\sum \text{available\_weights}}$$
- Computes completeness confidence:
  $$\text{confidence} = \frac{\sum \text{available\_weights}}{\text{total\_expected\_weights}} \times 100$$
- In `financial.py`, handles zero or missing income by excluding income-dependent ratios rather than penalizing the user with zero score.

#### 4. Aggregation & Trends (`aggregation.py`)
- `calculate_overall_score`: Blends category scores using weights (Health 40%, Financial 35%, Social 25%), renormalizing across categories that have confidence $> 0$.
- `calculate_recency_weighted_score`:
  For each historical daily score $d$ days ago:
  $$\text{recency\_weight} = e^{-\lambda \cdot d}$$
  $$\text{effective\_weight} = \text{recency\_weight} \times \left(\frac{\text{confidence}}{100}\right)$$
  $$\text{Period Score} = \frac{\sum (\text{score} \times \text{effective\_weight})}{\sum \text{effective\_weight}}$$
  $$\text{Period Confidence} = \frac{\sum (\text{confidence} \times \text{recency\_weight})}{\sum \text{recency\_weight}}$$
- `calculate_trend`:
  Compares recent 7-day score against previous 7-day score (days 7–13). Returns `"improving"` if $\Delta \ge +5.0$, `"declining"` if $\Delta \le -5.0$, `"stable"` otherwise, or `"insufficient_data"` if $< 2$ days of data exist.

#### 5. Scoring Service & Upsert (`service.py`)
- `calculate_daily_score(user, score_date)`:
  Calculates category scores, category confidences, overall score, and overall confidence.
  Performs an **idempotent upsert** in `Wellbeing Daily Score` matching `(user, score_date, scoring_version)`. Repeated calls update the existing row rather than duplicating records.
- `get_user_dashboard(user, as_of_date)`:
  Queries the last 90 days of scores for the user.
  Computes today score, 30-day score, 7-day score, 90-day score, confidences, and trends for Health, Financial, Social, and Overall. Returns the complete dashboard data structure.

---

### 3.6 DocType Controllers & Validations (`well_pro/well_pro_app/doctype/*/*.py`)

Controllers inherit from `frappe.model.document.Document` and implement server-side integrity rules:

1. **`HealthDailyRecord`** (`health_daily_record.py`):
   - `validate_unique_date()`: Ensures a user cannot insert a second `Health Daily Record` for the same date (`frappe.DuplicateEntryError`).
   - `validate_ranges()`: Verifies ratings (`sleep_quality`, `energy_level`, `self_rated_health`) are between 1 and 5; verifies durations, steps, liters, and grams are $\ge 0$.
2. **`SubjectiveWellbeingCheckin`** (`subjective_wellbeing_checkin.py`):
   - `validate_unique_date()`: Ensures one check-in per user per calendar day.
   - `validate_ratings()`: Enforces ratings (`mood`, `energy`, `stress`, `social_connection`, `loneliness`, `social_satisfaction`, `financial_stress`) strictly in `1..5`.
3. **`FinancialTransaction`** (`financial_transaction.py`):
   - Enforces `amount > 0` (`frappe.ValidationError`).
4. **`FinancialSnapshot`** (`financial_snapshot.py`):
   - Enforces non-negative asset and expense balances; verifies `financial_stress_rating` is in `1..5`.
5. **`SocialActivity`** (`social_activity.py`):
   - Verifies `interaction_quality`, `connection_level`, `mood_after` are in `1..5`; verifies `duration_minutes >= 0`.
6. **`HealthActivity`** (`health_activity.py`):
   - Enforces non-negative durations, distances, steps, and calories.
7. **`WellProProfile`** (`wellpro_profile.py`):
   - Enforces `height_cm > 0`.
8. **`WellbeingDailyScore`** (`wellbeing_daily_score.py`):
   - Enforces scores and confidences are in `0.0 – 100.0`.

---

## 4. Development Seed Data (`well_pro/well_pro_app/seed.py`)

A development seeder is included to set up realistic local test data without hardcoding mock fixtures into production migrations.

### How to Execute:
```bash
bench --site well-pro execute well_pro.well_pro_app.seed.seed_development_data
```

### Data Populated:
1. **Financial Categories**: Salary & Wages, Freelance, Groceries, Rent, Utilities, Dining, Health/Fitness, Index Investments, Student Loans, Emergency Transfers.
2. **User A (`user_a@wellpro.test` / `WellProPassword123!`)**:
   - 30 continuous days of health daily records.
   - 15 workout activities.
   - 20+ financial transactions across income, expenses, investments, and debt payments.
   - 2 financial snapshots (30 days ago and current).
   - 15 social activities.
   - 25 subjective wellbeing check-ins.
   - 30 daily wellbeing score records calculated with `v1` algorithm.
3. **User B (`user_b@wellpro.test` / `WellProPassword123!`)**:
   - Edge cases for isolation and confidence testing:
     - Day with no sleep recorded (confidence testing).
     - Day with only health data (category weight renormalization testing).
     - Day with only social data.
     - Snapshot without income (zero-income safety testing).
     - High loneliness reflection (inverse rating testing).

---

## 5. Automated Test Suite (`well_pro/well_pro_app/tests/`)

The test suite is structured into standalone mathematical unit tests and Frappe integration tests:

1. **`test_normalization.py`** (14 unit tests):
   - Validates clamping to `[0.0, 100.0]`.
   - Validates 1–5 rating conversions ($1\rightarrow 0, 5\rightarrow 100$).
   - Validates inverse rating conversions ($1\rightarrow 100, 5\rightarrow 0$).
   - Validates progress towards targets (e.g. 10,000 steps).
   - Validates target range plateau and linear slope decay (e.g. 7–9 hrs sleep).
   - Validates `None` and non-numeric input handling.
2. **`test_aggregation.py`** (Recency decay & trend tests):
   - Validates overall score category blending (Health 40%, Financial 35%, Social 25%).
   - Validates missing category renormalization.
   - Validates mathematical exponential half-life decay curve values:
     - Day 0: 100%
     - Day 7: 70.7%
     - Day 14: 50.0%
     - Day 28: 25.0%
   - Validates daily confidence weighting in period calculations.
   - Validates trend classifications (`improving`, `declining`, `stable`, `insufficient_data`).
3. **`test_scoring_engine.py`** (Domain scoring tests with mocked db):
   - Mocks `frappe.local.db` to execute domain calculations without requiring MariaDB.
   - Validates complete health records, partial records, and empty days.
   - Validates healthy financial snapshots, missing income cases, and empty financial data.
   - Validates social interactions and loneliness inversion.
4. **`test_security_and_api.py`** (Frappe integration tests):
   - Validates allowlist blocks arbitrary DocTypes (`User`, `Role`, `System Settings`).
   - Validates user cannot spoof ownership on insert.
   - Validates User A cannot retrieve User B records (`get_user_records`).
   - Validates User A cannot update User B records (`update_record`).
   - Validates User A cannot delete User B records (`delete_record`).
   - Validates score recalculation idempotency (updates existing row, no duplicate rows).
   - Validates updating historical October 10 record recalculates October 10 score.

---

## 6. Ubuntu Bench Deployment & Verification Runbook

When deploying into your Ubuntu Frappe Bench environment, execute:

```bash
# 1. Navigate to bench directory
cd ~/frappe/frappe-bench

# 2. Run schema migration (creates MySQL tables, columns, and search indexes)
bench --site well-pro migrate

# 3. Clear cached DocTypes and bytecode
bench --site well-pro clear-cache

# 4. Restart Bench services (Redis, gunicorn, background workers)
bench restart

# 5. Populate development seed data
bench --site well-pro execute well_pro.well_pro_app.seed.seed_development_data

# 6. Run the complete automated test suite
bench --site well-pro run-tests --app well_pro
```
