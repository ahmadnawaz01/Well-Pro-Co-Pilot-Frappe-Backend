# WellPro Backend API Documentation

Welcome to the **WellPro / Well_pro_app** REST API documentation. WellPro provides multi-dimensional wellbeing tracking (Health, Financial, Social, and Subjective Check-in) powered by Frappe Framework (v14/v15).

---

## 1. Architecture & Protocol Overview

### Base URLs & Frappe Routing
All API methods are whitelisted Frappe RPC functions accessible at:
```
https://<your-frappe-host>/api/method/<method_path>
```
Standard package paths:
- Primary Path: `well_pro.well_pro_app.api.<method>`
- Backward Compatibility Alias: `well_pro.api.<method>`

### Authentication
WellPro supports two standard authentication mechanisms:
1. **API Key & Secret (Recommended for Mobile / Microservices / FastAPI)**:
   Pass as HTTP Header:
   ```http
   Authorization: token <api_key>:<api_secret>
   ```
2. **Frappe Cookie / Session Auth (Web App / Desk)**:
   Standard `sid` cookie created upon `/api/method/well_pro.well_pro_app.api.login`.

### Multi-User Isolation & Authoritative Identity
- Normal users can **only** view, update, and delete documents they own (`user == frappe.session.user`).
- Client-supplied `user` fields are **never trusted** from standard users and are automatically overridden with `frappe.session.user`.
- Generic CRUD endpoints enforce a strict **allowlist** of permitted WellPro DocTypes, completely blocking arbitrary system DocTypes (`User`, `Role`, `System Settings`, etc.).

### Response Wrapper Format
All WellPro API methods return a standard JSON structure. Because Frappe wraps method returns in a `{"message": ...}` envelope, responses appear as:

#### Success Response
```json
{
  "message": {
    "success": true,
    "message": "Resource created successfully",
    "data": { ... }
  }
}
```

#### Validation Failure (HTTP 400 / 417)
```json
{
  "exception": "frappe.exceptions.ValidationError: Transaction amount must be greater than zero",
  "exc_type": "ValidationError",
  "_server_messages": "..."
}
```

#### Authentication Failure (HTTP 401 / 403)
```json
{
  "exception": "frappe.exceptions.AuthenticationError: Unauthorized access",
  "exc_type": "AuthenticationError"
}
```

---

## 2. Permitted DocTypes Allowlist

The following DocTypes are permitted in generic CRUD operations (`insert_record`, `update_record`, `get_user_records`, `delete_record`):

| DocType Name | User Owned? | Primary Date Field | Description |
| :--- | :---: | :--- | :--- |
| `Health Daily Record` | Yes | `record_date` | Sleep, steps, active minutes, nutrition, hydration, daily health |
| `Health Activity` | Yes | `logged_at` | Individual workout / exercise activity logs |
| `Financial Transaction` | Yes | `transaction_date` | Incomes, expenses, transfers, investments, debt payments |
| `Financial Snapshot` | Yes | `snapshot_date` | Monthly balances, liquid assets, debt burden, stress ratings |
| `Financial Category` | No (System) | N/A | System-wide transaction categorization (read-only for normal users) |
| `Social Activity` | Yes | `logged_at` | Social interactions, relationship types, quality ratings |
| `Subjective Wellbeing Checkin` | Yes | `date` | Evening reflection, mood, energy, connection, loneliness |
| `User Consent Preference` | Yes | N/A | Feature toggles, AI/voice processing consent |
| `WellPro Profile` | Yes | N/A | User settings, height, timezone, preferred currency |
| `Wellbeing Daily Score` | Yes (Read Only)| `score_date` | Precalculated daily scores (0-100) and confidences |

---

## 3. Endpoints Specification

### 3.1 Authentication & User Management

#### `signup`
- **Purpose**: Registers a new user account, generates API credentials, and initializes default profile and consent documents. Standard users receive standard user privileges (never `System Manager`).
- **HTTP Method**: `POST`
- **Path**: `well_pro.well_pro_app.api.signup`
- **Auth Required**: No (`allow_guest=True`)
- **Headers**: `Content-Type: application/json`
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "StrongPassword123!",
    "first_name": "Jane",
    "last_name": "Doe"
  }
  ```
- **Success Response**:
  ```json
  {
    "message": {
      "success": true,
      "message": "User registered successfully",
      "data": {
        "user": "user@example.com",
        "api_key": "3f8a9b2c1d0e4f5",
        "api_secret": "9a8b7c6d5e4f3a2"
      }
    }
  }
  ```
- **Example cURL**:
  ```bash
  curl -X POST "http://localhost:8000/api/method/well_pro.well_pro_app.api.signup"     -H "Content-Type: application/json"     -d '{"email":"jane@example.com","password":"Password123!","first_name":"Jane"}'
  ```

---

#### `login`
- **Purpose**: Authenticates credentials and returns active API Key/Secret.
- **HTTP Method**: `POST`
- **Path**: `well_pro.well_pro_app.api.login`
- **Auth Required**: No (`allow_guest=True`)
- **Request Body**:
  ```json
  {
    "usr": "user@example.com",
    "pwd": "StrongPassword123!"
  }
  ```
- **Success Response**:
  ```json
  {
    "message": {
      "success": true,
      "message": "Authentication successful",
      "data": {
        "user": "user@example.com",
        "api_key": "3f8a9b2c1d0e4f5",
        "api_secret": "9a8b7c6d5e4f3a2"
      }
    }
  }
  ```

---

#### `verify_user_session`
- **Purpose**: Validates active session and retrieves user profile and consent settings.
- **HTTP Method**: `GET` or `POST`
- **Path**: `well_pro.well_pro_app.api.verify_user_session`
- **Auth Required**: Yes (`token` or session cookie)
- **Success Response**:
  ```json
  {
    "message": {
      "success": true,
      "message": "Session valid",
      "data": {
        "user": "user@example.com",
        "profile": { "timezone": "UTC", "height_cm": 175.0, ... },
        "consent": { "health_tracking_enabled": 1, ... }
      }
    }
  }
  ```

---

### 3.2 Data Ingestion & Mutation APIs

#### `insert_record`
- **Purpose**: Generic secure document creation endpoint. Automatically sets `user = frappe.session.user`, validates allowed DocTypes, strips protected fields, and recalculates the affected historical date's score.
- **HTTP Method**: `POST`
- **Path**: `well_pro.well_pro_app.api.insert_record`
- **Auth Required**: Yes
- **Score Recalculation Triggered?**: **Yes**, automatically for the date of the record.
- **Request Body**:
  ```json
  {
    "doctype": "Health Daily Record",
    "record_data": {
      "record_date": "2026-10-23",
      "sleep_hours": 8.0,
      "sleep_quality": 4,
      "steps": 10500,
      "water_liters": 2.5
    }
  }
  ```
- **Success Response**:
  ```json
  {
    "message": {
      "success": true,
      "message": "Health Daily Record created successfully",
      "data": {
        "name": "HLT-DLY-2026-10-00001",
        "user": "user@example.com",
        "record_date": "2026-10-23",
        "sleep_hours": 8.0,
        "steps": 10500
      }
    }
  }
  ```
- **cURL Example**:
  ```bash
  curl -X POST "http://localhost:8000/api/method/well_pro.well_pro_app.api.insert_record"     -H "Authorization: token API_KEY:API_SECRET"     -H "Content-Type: application/json"     -d '{"doctype":"Health Daily Record","record_data":{"record_date":"2026-10-23","sleep_hours":7.5,"steps":8000}}'
  ```

---

#### `store_ai_record`
- **Purpose**: Persists structured AI extracted records from voice, receipt OCR, or background agents. Maps domain strings (`health`, `financial`, `health_activity`, `social`, `wellbeing`) to specific DocTypes.
- **HTTP Method**: `POST`
- **Path**: `well_pro.well_pro_app.api.store_ai_record`
- **Auth Required**: Yes
- **Score Recalculation Triggered?**: **Yes**
- **Request Body**:
  ```json
  {
    "domain": "financial",
    "record_data": {
      "transaction_type": "Expense",
      "category": "Groceries & Food",
      "amount": 45.20,
      "transaction_date": "2026-10-23",
      "merchant_or_source": "Whole Foods",
      "source": "OCR Receipt"
    }
  }
  ```

---

#### `update_record`
- **Purpose**: Safely updates an existing user record. Verifies caller ownership, prevents mass assignment to system fields (`user`, `owner`, `creation`), and recalculates scores for the affected date (including old and new dates if date was changed).
- **HTTP Method**: `POST`
- **Path**: `well_pro.well_pro_app.api.update_record`
- **Auth Required**: Yes
- **Score Recalculation Triggered?**: **Yes**
- **Request Body**:
  ```json
  {
    "doctype": "Health Daily Record",
    "name": "HLT-DLY-2026-10-00001",
    "update_data": {
      "steps": 12500,
      "water_liters": 3.0
    }
  }
  ```

---

#### `delete_record`
- **Purpose**: Deletes a record owned by the authenticated caller and triggers score recalculation for the affected date.
- **HTTP Method**: `POST`
- **Path**: `well_pro.well_pro_app.api.delete_record`
- **Auth Required**: Yes
- **Score Recalculation Triggered?**: **Yes**
- **Request Body**:
  ```json
  {
    "doctype": "Health Activity",
    "name": "HEA-SNP-2026-10-00001"
  }
  ```

---

### 3.3 Retrieval, Scoring & Dashboard APIs

#### `get_user_records`
- **Purpose**: Retrieves paginated records for the authenticated user only.
- **HTTP Method**: `GET`
- **Path**: `well_pro.well_pro_app.api.get_user_records`
- **Auth Required**: Yes
- **Query Parameters**:
  - `doctype` (string, required): Allowed DocType name
  - `limit` (int, default: 50, max: 200): Page size
  - `offset` (int, default: 0): Page start offset
  - `order_by` (string, default: "modified desc"): Sort column and order
  - `from_date` (string, optional): Filter start date (`YYYY-MM-DD`)
  - `to_date` (string, optional): Filter end date (`YYYY-MM-DD`)
- **Success Response**:
  ```json
  {
    "message": {
      "success": true,
      "message": "Success",
      "data": [ ... ],
      "count": 30,
      "limit": 50,
      "offset": 0
    }
  }
  ```
- **cURL Example**:
  ```bash
  curl -G "http://localhost:8000/api/method/well_pro.well_pro_app.api.get_user_records"     -H "Authorization: token API_KEY:API_SECRET"     -d "doctype=Health Daily Record"     -d "limit=10"     -d "from_date=2026-10-01"
  ```

---

#### `recalculate_score`
- **Purpose**: Explicitly recalculates the daily score for the authenticated user for a specified date.
- **HTTP Method**: `POST`
- **Path**: `well_pro.well_pro_app.api.recalculate_score`
- **Auth Required**: Yes
- **Request Body**:
  ```json
  {
    "date": "2026-10-23"
  }
  ```
- **Success Response**:
  ```json
  {
    "message": {
      "success": true,
      "message": "Wellbeing score for 2026-10-23 calculated successfully",
      "data": {
        "score_date": "2026-10-23",
        "health_score": 88.5,
        "health_confidence": 92.0,
        "financial_score": 82.0,
        "financial_confidence": 100.0,
        "social_score": 85.0,
        "social_confidence": 85.0,
        "overall_score": 85.4,
        "scoring_version": "v1"
      }
    }
  }
  ```

---

#### `get_dashboard`
- **Purpose**: Returns the full multi-dimensional Wellbeing Dashboard data for the authenticated user, featuring current scores, exponential recency-weighted period scores (7-day, 30-day, 90-day), confidences, and trend classifications.
- **HTTP Method**: `GET`
- **Path**: `well_pro.well_pro_app.api.get_dashboard`
- **Auth Required**: Yes
- **Query Parameters**:
  - `as_of_date` (string, optional, defaults to today): Calculation reference date
- **Success Response**:
  ```json
  {
    "message": {
      "success": true,
      "message": "Dashboard metrics retrieved successfully",
      "data": {
        "health": {
          "today_score": 88.1,
          "current_score": 82.4,
          "confidence": 91.0,
          "seven_day_score": 85.3,
          "thirty_day_score": 82.4,
          "ninety_day_score": 78.7,
          "trend": "improving",
          "trend_change": 6.2
        },
        "financial": {
          "today_score": 80.0,
          "current_score": 79.5,
          "confidence": 85.0,
          "seven_day_score": 80.0,
          "thirty_day_score": 79.5,
          "ninety_day_score": 75.0,
          "trend": "stable",
          "trend_change": 1.5
        },
        "social": {
          "today_score": 90.0,
          "current_score": 84.0,
          "confidence": 80.0,
          "seven_day_score": 88.0,
          "thirty_day_score": 84.0,
          "ninety_day_score": 81.2,
          "trend": "improving",
          "trend_change": 5.8
        },
        "overall": {
          "score": 81.8,
          "today_score": 85.7,
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
- **cURL Example**:
  ```bash
  curl -G "http://localhost:8000/api/method/well_pro.well_pro_app.api.get_dashboard"     -H "Authorization: token API_KEY:API_SECRET"
  ```

---

### 6. Scoring Goals & Personal Heuristics Configuration

#### `setup_scoring_goals` / `set_scoring_goals`
Allows an authenticated user to customize their wellbeing scoring targets (e.g. 10000 steps, financial budget 10k, 20% savings rate). Inputs can be provided as numbers or human-friendly strings (e.g. `"10k"`, `"20%"`, `"2500ml"`, `"$10,000"`), which are automatically parsed and converted into the engine's config scale.
If a user does not customize a goal, the default baseline heuristic from `config.py` is applied.

- **HTTP Method**: POST
- **Path**: `well_pro.well_pro_app.api.setup_scoring_goals` (alias: `well_pro.well_pro_app.api.set_scoring_goals`)
- **Auth Required**: Yes
- **Parameters / Payload**:
  - `steps` (int/str, optional): Target daily steps (e.g. `"10k"`, `10000`, `"8,000"`)
  - `financial_budget` / `budget` (float/int/str, optional): Monthly spending budget (e.g. `"10k"`, `"$10,000"`, `10000.0`)
  - `savings_rate` / `target_savings_rate` (float/str, optional): Target savings rate (e.g. `"20%"`, `20`, `0.20`)
  - `active_minutes` (int/str, optional): Daily active minutes (e.g. `30`, `"30m"`, `"0.5h"`)
  - `exercise_minutes` (int/str, optional): Daily exercise minutes (e.g. `45`, `"45m"`, `"1h"`)
  - `water` / `water_liters` (float/str, optional): Daily hydration target (e.g. `"2.5L"`, `"2500ml"`, `2.5`)
  - `sleep_min` / `sleep_max` (float/str, optional): Optimal sleep hours (e.g. `"7h"`, `7.5`)
  - `goals` (dict/json string, optional): Nested dictionary of goals
  - `recalculate` (bool, optional, default: true): Whether to trigger immediate daily score recalculation
  - `reset` (bool, optional, default: false): If true, resets all custom goals back to default config heuristics
- **Example cURL Request**:
  ```bash
  curl -X POST "http://localhost:8000/api/method/well_pro.well_pro_app.api.setup_scoring_goals" \
    -H "Authorization: token API_KEY:API_SECRET" \
    -H "Content-Type: application/json" \
    -d '{
      "steps": "10k",
      "financial_budget": "10k",
      "savings_rate": "20%"
    }'
  ```
- **Example Response**:
  ```json
  {
    "message": {
      "success": true,
      "message": "Scoring goals updated and converted to config scale successfully",
      "data": {
        "user": "user@wellpro.test",
        "configured_goals": {
          "steps_target": 10000,
          "budget_amount": 10000.0,
          "target_savings_rate": 0.20
        },
        "all_custom_goals": {
          "steps_target": 10000,
          "budget_amount": 10000.0,
          "target_savings_rate": 0.20
        },
        "effective_config": {
          "steps_target": 10000,
          "budget_amount": 10000.0,
          "target_savings_rate": 0.20,
          "active_minutes_target": 30,
          "exercise_minutes_target": 45,
          "sleep_optimal_min": 7.0,
          "sleep_optimal_max": 9.0,
          "water_liters_target": 2.5
        },
        "recalculated_score": {
          "health_score": 92.5,
          "financial_score": 88.0,
          "social_score": 85.0,
          "overall_score": 89.2
        }
      }
    }
  }
  ```

#### `get_scoring_goals`
Retrieves the user's custom goals, the original default baseline config, and the effective active configuration.

- **HTTP Method**: GET
- **Path**: `well_pro.well_pro_app.api.get_scoring_goals`
- **Auth Required**: Yes
- **Example cURL Request**:
  ```bash
  curl -G "http://localhost:8000/api/method/well_pro.well_pro_app.api.get_scoring_goals" \
    -H "Authorization: token API_KEY:API_SECRET"
  ```
