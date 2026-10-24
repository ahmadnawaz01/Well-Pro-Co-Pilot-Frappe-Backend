<div align="center">

# 🌿 WellPro (Well_pro_app)

**An Industry-Grade, Multi-Dimensional Wellbeing & Holistic Health Tracking Platform**

[![Frappe Framework](https://img.shields.io/badge/Frappe-v14%20%2F%20v15-blue.svg?style=for-the-badge&logo=frappe)](https://frappeframework.com)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)
[![Build Status](https://img.shields.io/badge/Tests-Passing-brightgreen.svg?style=for-the-badge)](#6-testing--verification)
[![Security Hardened](https://img.shields.io/badge/Security-Hardened%20%26%20Isolated-red.svg?style=for-the-badge)](#4-security--architecture-hardening)

<p align="center">
  <a href="#-key-features">Key Features</a> •
  <a href="#-architecture--scoring-engine">Scoring Engine</a> •
  <a href="#-installation--setup">Setup Guide</a> •
  <a href="#-api-reference--curl-examples">API Reference</a> •
  <a href="#-doc-type-schemas--data-models">Data Models</a> •
  <a href="#-testing--verification">Testing</a>
</p>

---

</div>

## 📌 Executive Overview

**WellPro** (`well_pro` / `Well_pro_app`) is an enterprise-ready backend platform built on top of the **Frappe Framework**. It provides real-time tracking, AI-powered extraction, and algorithmic scoring across four critical dimensions of human wellbeing:

1. 🏃 **Physical Health**: Sleep duration/quality, workouts, step count, hydration, calories, protein, and vitality energy.
2. 💰 **Financial Health**: Savings rates, expense ratios, debt-to-income service, emergency fund coverage, and financial stress.
3. 👥 **Social Connection**: Interaction quality, relational depth, community engagement, loneliness mitigation, and post-interaction mood impact.
4. 🧘 **Subjective Check-Ins**: Daily evening reflections tracking mood, stress, energy, and fulfillment.

WellPro features a **v1 Decoupled Scoring Engine** that normalizes heterogeneous metrics onto a continuous $0.0 - 100.0$ scale, renormalizes weights for missing data, computes historical exponential recency decay ($14$-day half-life), and detects period-over-period trend vectors.

---

## ✨ Key Features

* **🔒 Enterprise Multi-Tenant Security**: Strict session caller isolation (`frappe.session.user` authority), protected metadata field stripping, and complete prevention of mass-assignment vulnerabilities.
* **🛡️ DocType Allowlist Engine**: Restricts generic CRUD endpoints strictly to designated WellPro DocTypes, preventing unauthorized injection into system tables (`User`, `Role`, `System Settings`).
* **📊 Mathematical Scoring Engine**: Environment-independent normalization algorithms (`HIGHER_IS_BETTER`, `LOWER_IS_BETTER`, `TARGET_RANGE`, `RATING`, `INVERSE_RATING`) with dynamic weight renormalization and confidence tracking.
* **📈 Historical Recency & Trend Engine**: Calculates 7-day, 30-day, and 90-day exponentially weighted period scores and classifies trend shifts (`improving`, `declining`, `stable`).
* **🤖 AI Agent Ready**: Structured endpoints (`store_ai_record`) designed for LLM tool calling, voice transcripts, and OCR receipt processing.
* **⏱️ Nightly Cron Worker**: Automated background worker that processes daily wellbeing scores across active users.

---

## 🏗️ Architecture & Scoring Engine

### Scoring Pipeline

```
  RAW SOURCES                   NORMALIZATION                       DOMAINS                  PERIOD & TRENDS
┌───────────────┐          ┌───────────────────────┐          ┌───────────────────┐       ┌────────────────────┐
│ Health Logs   │ ───────► │ Target Range (Sleep)  │ ───────► │ Health Score      │ ────┐ │ 7-Day Window       │
│ Financial Snap│ ───────► │ Inverse Rating(Stress)│ ───────► │ Financial Score   │ ──┼─┼►│ 30-Day Window      │
│ Social Checkin│ ───────► │ Goal Scale (Steps)    │ ───────► │ Social Score      │ ────┘ │ 90-Day Window      │
└───────────────┘          └───────────────────────┘          └───────────────────┘       └────────────────────┘
                                                                        │                           │
                                                                        ▼                           ▼
                                                               ┌───────────────────┐       ┌────────────────────┐
                                                               │  Overall Score    │       │ Trend Vector       │
                                                               │ (Health 40/Fin 35)│       │ (Δ Recent vs Prev) │
                                                               └───────────────────┘       └────────────────────┘
```

### Mathematical Formulation

#### 1. Weight Renormalization (Missing Data Safety)
Users are never penalized with zero scores for unrecorded metrics. The domain score scales across available data:
$$\text{Domain Score} = \frac{\sum_{i \in \text{Available}} (\text{Metric Score}_i \times \text{Weight}_i)}{\sum_{i \in \text{Available}} \text{Weight}_i}$$

$$\text{Confidence (\%)} = \frac{\sum_{i \in \text{Available}} \text{Weight}_i}{\text{Total Expected Weight}} \times 100$$

#### 2. Exponential Half-Life Decay ($t_{1/2} = 14\text{ days}$)
To calculate historical 7d/30d/90d averages, daily scores decay with $\lambda = \frac{\ln(2)}{14} \approx 0.04951$:
$$\text{Recency Weight}(d) = e^{-\lambda \cdot d}$$
$$\text{Effective Weight}(d) = \text{Recency Weight}(d) \times \left(\frac{\text{Confidence}(d)}{100}\right)$$

#### 3. Trend Vector Classification
Compares the recent 7-day score (days 0–6) to the previous 7-day score (days 7–13):
$$\Delta = \text{Score}_{\text{Recent 7d}} - \text{Score}_{\text{Previous 7d}}$$

* **Improving**: $\Delta \ge +5.0$
* **Declining**: $\Delta \le -5.0$
* **Stable**: $-5.0 < \Delta < +5.0$

---

## 📂 Project Structure

```
well_pro/
├── docs/                                  # Developer & Architecture Specifications
│   ├── API.md                             # Comprehensive REST API reference & cURL guide
│   ├── CODE_REVIEW.md                     # Security audit, bug refactoring & code review
│   ├── SCORING.md                         # Mathematical scoring specification (v1)
│   ├── UBUNTU_TESTING.md                  # Deployment & testing runbook
│   └── doctype.md                         # DocType Schemas & Agent Tool Calling Guide
├── testing/json/                          # 22 Standalone JSON Request & Security Payloads
└── well_pro/                              # Application Root Package
    ├── api.py                             # Proxy routing layer (`well_pro.api`)
    ├── hooks.py                           # Scheduler events & Frappe hooks
    └── well_pro_app/                      # Core Business Logic Module
        ├── api.py                         # Whitelisted RPC API endpoints & CRUD controllers
        ├── tasks.py                       # Nightly scoring cron worker
        ├── seed.py                        # Continuous 30-day development database seeder
        ├── doctype/                       # 10 Custom Frappe DocTypes
        ├── services/scoring/              # Modular Decoupled Scoring Service
        │   ├── config.py                  # Domain weights, targets & parameters
        │   ├── normalization.py           # Pure math normalizer functions
        │   ├── health.py                  # Physical health domain engine
        │   ├── financial.py               # Financial health domain engine
        │   ├── social.py                  # Social connection domain engine
        │   ├── aggregation.py             # Exponential decay & trend calculator
        │   └── service.py                 # Dashboard builder & idempotent upsert
        └── tests/                         # Automated Unit & Integration Suite
            ├── test_normalization.py      # Mathematical unit tests
            ├── test_aggregation.py        # Exponential decay & trend tests
            ├── test_scoring_engine.py     # Domain scoring unit tests
            └── test_security_and_api.py   # Isolation & API security integration tests
```

---

## 🔒 Security & Architecture Hardening

During code review and refactoring, the following production security enhancements were implemented:

* **Privilege Escalation Neutralized**: Default user signup (`signup`) assigns basic user privileges (`System User`), completely removing default administrative (`System Manager`) assignment.
* **DocType Allowlist Enforcement**: Requests attempting arbitrary DocType access are rejected by `ALLOWED_DOCTYPES`.
* **User Identity Anti-Spoofing**: Generic creation endpoints ignore client-supplied `user` fields and bind `frappe.session.user` as the immutable record owner.
* **Mass-Assignment Guard**: Strips system-controlled fields (`owner`, `creation`, `modified_by`, `docstatus`, `idx`) on updates.
* **Database Optimization**: Added `search_index: 1` on `user` and date columns across all 10 DocTypes to prevent full table scans.

---

## 🚀 Installation & Setup

### Prerequisites
* **Ubuntu Linux** (20.04 LTS / 22.04 LTS recommended)
* **Frappe Bench**: v14 or v15
* **Python**: 3.10+
* **MariaDB**: 10.6+

### Step-by-Step Installation

```bash
# 1. Clone app into your Frappe Bench apps directory
cd ~/frappe/frappe-bench/apps
git clone https://github.com/your-org/well_pro.git

# 2. Install app into your bench Python environment
cd ~/frappe/frappe-bench
bench get-app well_pro

# 3. Install app onto your target site
bench --site well-pro install-app well_pro

# 4. Migrate database schemas and build database search indexes
bench --site well-pro migrate

# 5. Clear bench cache and restart services
bench --site well-pro clear-cache
bench restart
```

### Seeding Development Data
Populate 30 continuous days of test records for **User A** and edge-case scenarios for **User B**:

```bash
bench --site well-pro execute well_pro.well_pro_app.seed.seed_development_data
```

---

## 🧪 Testing & Verification

WellPro comes with a test suite covering pure math functions, mock domain evaluations, and live integration tests:

```bash
# Run complete test suite via Frappe Bench
bench --site well-pro run-tests --app well_pro

# Run individual test modules
bench --site well-pro run-tests --module well_pro.well_pro_app.tests.test_normalization
bench --site well-pro run-tests --module well_pro.well_pro_app.tests.test_aggregation
bench --site well-pro run-tests --module well_pro.well_pro_app.tests.test_scoring_engine
bench --site well-pro run-tests --module well_pro.well_pro_app.tests.test_security_and_api
```

---

## 📡 API Reference & cURL Examples

### Base Endpoint Structure
`https://<your-frappe-host>/api/method/well_pro.well_pro_app.api.<method>`

### 1. User Signup
* **Method**: `POST`
* **Path**: `/api/method/well_pro.well_pro_app.api.signup`
* **Auth Required**: No

```bash
curl -X POST "http://localhost:8000/api/method/well_pro.well_pro_app.api.signup" \
     -H "Content-Type: application/json" \
     -d '{
       "email": "jane@example.com",
       "password": "StrongPassword123!",
       "first_name": "Jane",
       "last_name": "Doe"
     }'
```

### 2. User Login
* **Method**: `POST`
* **Path**: `/api/method/well_pro.well_pro_app.api.login`
* **Auth Required**: No

```bash
curl -X POST "http://localhost:8000/api/method/well_pro.well_pro_app.api.login" \
     -H "Content-Type: application/json" \
     -d '{
       "usr": "jane@example.com",
       "pwd": "StrongPassword123!"
     }'
```

### 3. Record Data Insertion (`insert_record`)
* **Method**: `POST`
* **Path**: `/api/method/well_pro.well_pro_app.api.insert_record`
* **Auth Required**: Yes (`Authorization: token <api_key>:<api_secret>`)

```bash
curl -X POST "http://localhost:8000/api/method/well_pro.well_pro_app.api.insert_record" \
     -H "Authorization: token YOUR_API_KEY:YOUR_API_SECRET" \
     -H "Content-Type: application/json" \
     -d '{
       "doctype": "Health Daily Record",
       "record_data": {
         "record_date": "2026-10-23",
         "sleep_hours": 8.0,
         "sleep_quality": 4,
         "steps": 10500,
         "water_liters": 2.5
       }
     }'
```

### 4. Fetch Multi-Dimensional Wellbeing Dashboard (`get_dashboard`)
* **Method**: `GET`
* **Path**: `/api/method/well_pro.well_pro_app.api.get_dashboard`
* **Auth Required**: Yes

```bash
curl -G "http://localhost:8000/api/method/well_pro.well_pro_app.api.get_dashboard" \
     -H "Authorization: token YOUR_API_KEY:YOUR_API_SECRET"
```

#### Response Example
```json
{
  "message": {
    "success": true,
    "message": "Dashboard metrics retrieved successfully",
    "data": {
      "health": {
        "today_score": 88.1,
        "seven_day_score": 85.3,
        "thirty_day_score": 82.4,
        "ninety_day_score": 78.7,
        "confidence": 91.0,
        "trend": "improving",
        "trend_change": 6.2
      },
      "financial": {
        "today_score": 80.0,
        "seven_day_score": 80.0,
        "thirty_day_score": 79.5,
        "ninety_day_score": 75.0,
        "confidence": 85.0,
        "trend": "stable",
        "trend_change": 1.5
      },
      "social": {
        "today_score": 90.0,
        "seven_day_score": 88.0,
        "thirty_day_score": 84.0,
        "ninety_day_score": 81.2,
        "confidence": 80.0,
        "trend": "improving",
        "trend_change": 5.8
      },
      "overall": {
        "score": 81.8,
        "seven_day_score": 84.1,
        "thirty_day_score": 81.8,
        "ninety_day_score": 78.1,
        "trend": "improving",
        "trend_change": 5.1
      },
      "scoring_version": "v1",
      "as_of_date": "2026-10-23"
    }
  }
}
```

---

## 📋 DocType Schemas & Data Models

| DocType Name | Domain Key | User Owned | Date Field | Description |
| :--- | :---: | :---: | :--- | :--- |
| `Health Daily Record` | `"health"` | Yes | `record_date` | Aggregated daily physical health metrics |
| `Health Activity` | `"health_activity"` | Yes | `logged_at` | Workout logs (running, cycling, gym, sports) |
| `Financial Transaction` | `"financial"` | Yes | `transaction_date` | Incomes, expenses, investments, debt service |
| `Financial Snapshot` | N/A | Yes | `snapshot_date` | Periodic balance sheet, savings, emergency reserves |
| `Financial Category` | N/A | No (System) | N/A | Global expense/income classifications |
| `Social Activity` | `"social"` | Yes | `logged_at` | Interpersonal interactions & connection quality |
| `Subjective Wellbeing Checkin` | `"wellbeing"` | Yes | `date` | Evening reflection, mood, energy, loneliness |
| `User Consent Preference` | N/A | Yes | N/A | Privacy preferences & AI processing toggles |
| `WellPro Profile` | N/A | Yes | N/A | User settings, height, timezone, currency |
| `Wellbeing Daily Score` | N/A | Yes (Read-Only) | `score_date` | Calculated score storage ($0.0 - 100.0$) |

---

## 🤝 Contributing & Guidelines

1. **Code Style**: Format Python code using `ruff` or `black`.
2. **Database Changes**: Make modifications via Frappe Desk in Developer Mode and export schema updates using `bench export-fixtures`.
3. **Tests**: Ensure all new endpoints or normalizer algorithms have corresponding unit tests in `well_pro/well_pro_app/tests/`.

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.