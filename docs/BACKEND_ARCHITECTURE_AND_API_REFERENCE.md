# WellPro Backend Architecture, DocType Schema & Frontend Integration Guide

> **Version**: 2.0.0  
> **Target Audience**: Frontend Engineers, Mobile Developers, AI Integration Engineers, Senior Backend Maintainers  
> **Status**: Verified & Active

---

## Table of Contents
1. [Architecture Overview & Core Concepts](#1-architecture-overview--core-concepts)
2. [Authentication & Security Protocol](#2-authentication--security-protocol)
3. [DocTypes Schema Reference (All 10 Models)](#3-doctypes-schema-reference-all-10-models)
4. [Automatic Scoring Engine Mechanics](#4-automatic-scoring-engine-mechanics)
5. [Complete REST API Reference](#5-complete-rest-api-reference)
   - [5.1 User Authentication Endpoints](#51-user-authentication-endpoints)
   - [5.2 Data Ingestion & Creation Endpoints (Single, Batch & Multi-DocType)](#52-data-ingestion--creation-endpoints)
   - [5.3 Record Modification & Eviction Endpoints](#53-record-modification--eviction-endpoints)
   - [5.4 Data Querying & Retrieval Endpoints](#54-data-querying--retrieval-endpoints)
   - [5.5 Dashboard & Score Analytics Endpoints](#55-dashboard--score-analytics-endpoints)
   - [5.6 Scoring Goals Configuration Endpoints](#56-scoring-goals-configuration-endpoints)
6. [Frontend Integration Patterns (TypeScript / Axios / Fetch)](#6-frontend-integration-patterns)

---

## 1. Architecture Overview & Core Concepts

WellPro is a Frappe-based backend engine for holistic wellbeing intelligence covering **Health**, **Finance**, and **Social** dimensions.

### Key Architectural Tenets:
1. **Multi-User Isolation**: Every record is securely scoped to the authenticated caller (`user`). Normal users can never access, insert, or modify another user's records.
2. **Multi-DocType Ingestion**: Endpoints accept single records, flat dictionaries, arrays of records across multiple DocTypes, and multi-DocType composite payloads in a single request.
3. **Idempotent Daily Upserts**: Submitting multiple health logs, financial snapshots, or subjective check-ins on the same date will automatically accumulate and update the existing daily document without `DuplicateEntryError`.
4. **Immediate & Event-Driven Score Recalculation**:
   - Any insertion or update automatically triggers score recalculation for that specific date.
   - Ingestion endpoints return the recalculated score directly in the response payload, eliminating round-trips.
   - Frappe document hooks (`doc_events`) capture changes from Frappe Desk, REST APIs, or background workers.
5. **High-Performance Dashboard Engine**: `get_dashboard_metrics` refreshes current scores, computes multi-window recency-weighted scores (7d, 30d, 90d), and returns historical timelines and recent domain feeds in optimized queries.

---

## 2. Authentication & Security Protocol

### 2.1 Base URLs & Routing
Endpoints are accessible via both the top-level compatibility alias and the app module path:
```http
POST /api/method/well_pro.api.<method_name>
POST /api/method/well_pro.well_pro_app.api.<method_name>
```

### 2.2 Authorization Header
Protected endpoints require API Token authentication:
```http
Authorization: token <api_key>:<api_secret>
Content-Type: application/json
```

### 2.3 Response Standard Envelope
All WellPro endpoints return responses formatted as:
```json
{
  "message": {
    "success": true,
    "message": "Descriptive message",
    "data": { ... }
  }
}
```
*Note*: Frappe automatically wraps whitelisted returns inside top-level `"message"`. In your HTTP client (e.g. Axios), inspect `response.data.message`.

---

## 3. DocTypes Schema Reference (All 10 Models)

| DocType | Scope | Primary Date Field | Description |
|---|---|---|---|
| **Health Daily Record** | User | `record_date` | Aggregated daily health metrics (steps, sleep, calories, water) |
| **Health Activity** | User | `logged_at` | Individual workout and fitness sessions (runs, walks, gym) |
| **Financial Transaction** | User | `transaction_date` | Individual income, expense, and transfer ledger entries |
| **Financial Snapshot** | User | `snapshot_date` | Aggregated financial status, emergency fund, and debt balances |
| **Financial Category** | System | `creation` | Transaction category classifications with auto-generation |
| **Social Activity** | User | `logged_at` | Social interactions, connections, and relationship ratings |
| **Subjective Wellbeing Checkin** | User | `date` | Self-reported daily mood, energy, and stress check-ins |
| **Wellbeing Daily Score** | User | `score_date` | System-computed daily scores (0-100) and confidence values |
| **User Consent Preference** | User | `consent_updated_at` | AI and domain tracking consent flags |
| **WellPro Profile** | User | `creation` | Personal settings, currency, and custom scoring goals |

---

### 3.1 Health Daily Record
- **Unique Constraint**: `(user, record_date)`
- **Auto-Defaults**: `record_date` defaults to current date if omitted.

| Fieldname | Type | Req | Options / Constraints | Description |
|---|---|---|---|---|
| `user` | Link | Yes | `User` | Owner user |
| `record_date` | Date | Yes | YYYY-MM-DD | Target date |
| `sleep_hours` | Float | No | $\ge 0$ (Optimal 7.0 - 9.0) | Total hours of sleep |
| `sleep_quality` | Int | No | 1 - 5 | Subjective sleep rating |
| `steps` | Int | No | $\ge 0$ (Default Target: 10,000) | Step count (accumulative) |
| `active_minutes` | Int | No | $\ge 0$ (Default Target: 45) | Active minutes |
| `exercise_minutes` | Int | No | $\ge 0$ (Default Target: 30) | Exercise minutes |
| `exercise_intensity`| Select | No | `Low`, `Moderate`, `High` | Workout intensity |
| `water_liters` | Float | No | $\ge 0$ (Default Target: 2.5) | Water intake in liters |
| `calories_consumed`| Float | No | $\ge 0$ (Optimal 1800 - 2500) | Daily caloric intake |
| `protein_grams` | Float | No | $\ge 0$ (Default Target: 75.0) | Protein intake in grams |
| `fruit_veg_servings`| Float | No | $\ge 0$ (Default Target: 5.0) | Fruit and vegetable servings |
| `energy_level` | Int | No | 1 - 5 | Subjective daily energy |
| `self_rated_health`| Int | No | 1 - 5 | General health rating |
| `source` | Select | No | `Manual Entry`, `Voice`, `Wearable`, `AI Extraction`, `Import`, `Other` | Data provenance |

---

### 3.2 Health Activity
- **Multiple entries per day allowed**: Accumulates into Health Daily Record automatically.

| Fieldname | Type | Req | Options / Constraints | Description |
|---|---|---|---|---|
| `user` | Link | Yes | `User` | Owner user |
| `activity_type` | Select | Yes | `Walking`, `Running`, `Cycling`, `Gym`, `Sports`, `Other` (Default: `Other`) | Category of activity |
| `logged_at` | Datetime | Yes | YYYY-MM-DD HH:mm:ss (Defaults to `now()`) | Timestamp of session |
| `duration_minutes` | Float | No | $\ge 0$ | Duration in minutes |
| `distance_km` | Float | No | $\ge 0$ | Distance in kilometers |
| `steps` | Int | No | $\ge 0$ | Session step count |
| `calories_burned` | Float | No | $\ge 0$ | Active calories burned |
| `intensity` | Select | No | `Low`, `Moderate`, `High` | Workout intensity |
| `source` | Select | No | `Manual Entry`, `Voice`, `Wearable`, `AI Extraction`, `Other` | Source origin |
| `raw_input` | Text | No | Original text / transcript | Audit trail |

---

### 3.3 Financial Transaction
- **Ledger model**: Multiple transactions per day allowed. Accumulates into daily Financial Snapshot.

| Fieldname | Type | Req | Options / Constraints | Description |
|---|---|---|---|---|
| `user` | Link | Yes | `User` | Owner user |
| `transaction_type` | Select | Yes | `Income`, `Expense`, `Transfer`, `Investment`, `Debt Payment` (Default: `Expense`) | Transaction direction |
| `category` | Link | Yes | `Financial Category` (Auto-resolved/created) | Ledger category |
| `amount` | Currency | Yes | $> 0$ (Strictly positive) | Monetary value |
| `currency` | Link | No | `Currency` (e.g. USD, EUR, PKR) | ISO Currency code |
| `transaction_date` | Date | Yes | YYYY-MM-DD (Defaults to `today()`) | Date of transaction |
| `merchant_or_source`| Data | No | Merchant name, vendor, employer | Counterparty |
| `description` | Small Text| No | Brief memo | Memo / notes |
| `payment_method` | Select | No | `Cash`, `Bank`, `Card`, `Digital Wallet`, `Other` | Payment instrument |
| `is_recurring` | Check | No | 0 or 1 | Subscription / recurring flag |
| `essentiality` | Select | No | `Essential`, `Discretionary`, `Not Applicable` | Essential expense classification |
| `source` | Select | No | `Manual Entry`, `Voice`, `OCR Receipt`, `AI Extraction`, `Import`, `Bank Integration`, `Other` | Data source |
| `raw_input` | Text | No | OCR text / raw agent input | Audit trail |

---

### 3.4 Financial Snapshot
- **Unique Constraint**: `(user, snapshot_date)`

| Fieldname | Type | Req | Options / Constraints | Description |
|---|---|---|---|---|
| `user` | Link | Yes | `User` | Owner user |
| `snapshot_date` | Date | Yes | YYYY-MM-DD (Defaults to `today()`) | Snapshot date |
| `monthly_income` | Currency | No | $\ge 0$ | Total monthly income |
| `monthly_expenses` | Currency | No | $\ge 0$ | Total monthly expenses |
| `essential_monthly_expenses` | Currency | No | $\ge 0$ | Essential monthly overhead |
| `liquid_savings` | Currency | No | $\ge 0$ | Immediately accessible savings |
| `investment_value` | Currency | No | $\ge 0$ | Stocks, funds, crypto, assets |
| `emergency_fund` | Currency | No | $\ge 0$ (Default Target: 6 months expenses) | Cash reserve |
| `budget_amount` | Currency | No | $\ge 0$ | Monthly spending target |
| `outstanding_debt` | Currency | No | $\ge 0$ | Total liabilities |
| `monthly_debt_payment` | Currency | No | $\ge 0$ | Monthly debt servicing |
| `financial_stress_rating` | Int | No | 1 - 5 (Inverted scoring: 1=Low stress, 5=High) | Stress rating |
| `source` | Select | No | `Manual Entry`, `Import`, `Calculated` | Snapshot origin |

---

### 3.5 Social Activity
- **Multiple entries per day allowed**.

| Fieldname | Type | Req | Options / Constraints | Description |
|---|---|---|---|---|
| `user` | Link | Yes | `User` | Owner user |
| `logged_at` | Datetime | Yes | YYYY-MM-DD HH:mm:ss (Defaults to `now()`) | Interaction timestamp |
| `interaction_type` | Select | Yes | `In Person`, `Call`, `Video Call`, `Messaging`, `Group Activity`, `Community Activity`, `Other` | Medium of interaction |
| `relationship_type` | Select | Yes | `Family`, `Friend`, `Partner`, `Colleague`, `Community`, `Other` | Relationship context |
| `duration_minutes` | Float | No | $\ge 0$ | Interaction duration |
| `interaction_quality` | Int | No | 1 - 5 | Quality of the interaction |
| `connection_level` | Int | No | 1 - 5 | Closeness / warmth felt |
| `mood_after` | Int | No | 1 - 5 | Mood immediately following |
| `notes` | Small Text| No | Private memo | Context notes |
| `source` | Select | No | `Manual Entry`, `Voice`, `AI Extraction`, `Import`, `Other` | Origin |

---

### 3.6 Subjective Wellbeing Checkin
- **Unique Constraint**: `(user, date)`
- **Auto-Upserted**: Re-submitting on the same date updates the ratings.

| Fieldname | Type | Req | Options / Constraints | Description |
|---|---|---|---|---|
| `user` | Link | Yes | `User` | Owner user |
| `date` | Date | Yes | YYYY-MM-DD (Defaults to `today()`) | Check-in date |
| `mood` | Int | No | 1 - 5 (1=Very Poor, 5=Excellent) | Overall mood |
| `energy` | Int | No | 1 - 5 (1=Exhausted, 5=Energized) | Subjective energy |
| `stress` | Int | No | 1 - 5 (Inverted in scoring: 1=Low, 5=High) | General life stress |
| `social_connection` | Int | No | 1 - 5 (1=Isolated, 5=Connected) | Closeness to others |
| `loneliness` | Int | No | 1 - 5 (Inverted in scoring: 1=None, 5=Severe) | Feeling of loneliness |
| `social_satisfaction`| Int | No | 1 - 5 (1=Dissatisfied, 5=Satisfied) | Social life satisfaction |
| `financial_stress` | Int | No | 1 - 5 (Inverted in scoring: 1=Peaceful, 5=Extreme)| Financial anxiety |

---

### 3.7 Wellbeing Daily Score (Computed Output)
- **Computed automatically by backend engine**. Read-only for clients.

| Fieldname | Type | Description |
|---|---|---|
| `user` | Link | Scoped user |
| `score_date` | Date | Score calculation date (YYYY-MM-DD) |
| `health_score` | Float | Health wellbeing score (0.0 to 100.0) |
| `health_confidence` | Float | Confidence based on available components (0.0 to 100.0%) |
| `financial_score` | Float | Financial wellbeing score (0.0 to 100.0) |
| `financial_confidence`| Float | Confidence based on available components (0.0 to 100.0%) |
| `social_score` | Float | Social wellbeing score (0.0 to 100.0) |
| `social_confidence` | Float | Confidence based on available components (0.0 to 100.0%) |
| `overall_score` | Float | Confidence-weighted composite wellbeing score (0.0 to 100.0) |
| `scoring_version` | Data | Scoring algorithm version (e.g. `v1.0.0`) |
| `calculated_at` | Datetime | Exact timestamp of score evaluation |

---

## 4. Automatic Scoring Engine Mechanics

The scoring engine calculates scores from `0.0` to `100.0` across 3 domains:

### 4.1 Domain Metric Weights
- **Health (100 total)**: Sleep (30), Exercise (20), Activity/Steps (15), Nutrition (15), Hydration (10), Self-Rated/Energy (10).
- **Financial (100 total)**: Savings Rate (30), Expense/Budget Ratio (25), Debt Service Ratio (20), Emergency Reserve (15), Financial Stress (10).
- **Social (100 total)**: Interaction Quality (25), Connection Level (25), Social Satisfaction (20), Loneliness [Inverted] (15), Mood Impact (15).

### 4.2 Dynamic Renormalization & Confidence
If a user only logs sleep and steps on a given day:
- Sleep (30) + Steps (15) = 45 available weight.
- The score is normalized across the 45 available points: $\text{Score} = \frac{\sum(\text{Component} \times \text{Weight})}{45}$.
- The **confidence** is $\frac{45}{100} = 45.0\%$.

### 4.3 Multi-Window Recency Weighting
Historical dashboards utilize exponential decay with $\lambda = 0.05$ (14-day half-life):
$$w_i = e^{-\lambda \times \Delta t_i}$$
This powers 7-day, 30-day, and 90-day rolling scores where yesterday's behavior counts significantly more than activity from 3 weeks ago.

---

## 5. Complete REST API Reference

### 5.1 User Authentication Endpoints

#### `signup`
Registers a new user, generates API credentials, and initializes Profile & Consent models.
- **URL**: `/api/method/well_pro.well_pro_app.api.signup`
- **Method**: `POST`
- **Auth**: None (Public)
- **Input JSON**:
```json
{
  "email": "sarah.connor@example.com",
  "password": "SecurePassword123!",
  "first_name": "Sarah",
  "last_name": "Connor"
}
```
- **Output JSON (HTTP 200)**:
```json
{
  "message": {
    "success": true,
    "message": "User registered successfully",
    "data": {
      "user": "sarah.connor@example.com",
      "api_key": "4c9e88bf91a13b2",
      "api_secret": "9a7f34bc0281ef5"
    }
  }
}
```

---

#### `login`
Authenticates credentials and returns user API keys.
- **URL**: `/api/method/well_pro.well_pro_app.api.login`
- **Method**: `POST`
- **Auth**: None (Public)
- **Input JSON**:
```json
{
  "usr": "sarah.connor@example.com",
  "pwd": "SecurePassword123!"
}
```
- **Output JSON (HTTP 200)**:
```json
{
  "message": {
    "success": true,
    "message": "Authentication successful",
    "data": {
      "user": "sarah.connor@example.com",
      "api_key": "4c9e88bf91a13b2",
      "api_secret": "9a7f34bc0281ef5"
    }
  }
}
```

---

#### `verify_user_session`
Validates session credentials and returns Profile & Consent settings.
- **URL**: `/api/method/well_pro.well_pro_app.api.verify_user_session`
- **Method**: `GET` or `POST`
- **Auth**: `Authorization: token <api_key>:<api_secret>`
- **Output JSON (HTTP 200)**:
```json
{
  "message": {
    "success": true,
    "message": "Session valid",
    "data": {
      "user": "sarah.connor@example.com",
      "profile": {
        "name": "sarah.connor@example.com",
        "preferred_currency": "USD",
        "custom_scoring_goals": "{"steps_target": 12000}"
      },
      "consent": {
        "health_tracking_enabled": 1,
        "financial_tracking_enabled": 1,
        "social_tracking_enabled": 1,
        "allow_ai_processing": 1
      }
    }
  }
}
```

---

### 5.2 Data Ingestion & Creation Endpoints

#### `insert_record`
Universal ingestion endpoint supporting:
1. **Single Record (Nested)**: `{"doctype": "...", "record_data": {...}}`
2. **Single Record (Flat)**: `{"doctype": "Health Daily Record", "steps": 8500}`
3. **Batch Records Array**: `{"records": [{...}, {...}]}` or direct JSON array `[{...}, {...}]`
4. **Multi-DocType on Single Request**: Keyed by DocType name or domain alias!

- **URL**: `/api/method/well_pro.well_pro_app.api.insert_record`
- **Method**: `POST`
- **Auth**: Required

##### Format A: Multi-DocType on Single Request (Recommended for Full-Screen Forms)
```json
{
  "Health Daily Record": {
    "record_date": "2026-10-30",
    "steps": 9200,
    "sleep_hours": 7.5,
    "sleep_quality": 4,
    "water_liters": 2.2
  },
  "Financial Transaction": [
    {
      "transaction_date": "2026-10-30",
      "amount": 14.50,
      "category": "Coffee & Snacks",
      "transaction_type": "Expense",
      "payment_method": "Card"
    },
    {
      "transaction_date": "2026-10-30",
      "amount": 45.00,
      "category": "Groceries",
      "transaction_type": "Expense",
      "essentiality": "Essential"
    }
  ],
  "Social Activity": {
    "activity_name": "Team Lunch",
    "interaction_type": "In Person",
    "relationship_type": "Colleague",
    "interaction_quality": 4,
    "connection_level": 4
  },
  "Subjective Wellbeing Checkin": {
    "date": "2026-10-30",
    "mood": 4,
    "energy": 4,
    "stress": 2
  }
}
```

##### Success Response (HTTP 200) with Immediate Recalculated Scores:
```json
{
  "message": {
    "success": true,
    "message": "Successfully created 5 records",
    "data": {
      "count": 5,
      "affected_dates": ["2026-10-30"],
      "created": [
        {
          "index": 0,
          "doctype": "Health Daily Record",
          "name": "HDR-00042",
          "affected_date": "2026-10-30",
          "record": { ... }
        },
        {
          "index": 1,
          "doctype": "Financial Transaction",
          "name": "FT-00109",
          "affected_date": "2026-10-30",
          "record": { ... }
        },
        {
          "index": 2,
          "doctype": "Financial Transaction",
          "name": "FT-00110",
          "affected_date": "2026-10-30",
          "record": { ... }
        },
        {
          "index": 3,
          "doctype": "Social Activity",
          "name": "SOC-00018",
          "affected_date": "2026-10-30",
          "record": { ... }
        },
        {
          "index": 4,
          "doctype": "Subjective Wellbeing Checkin",
          "name": "CHK-00031",
          "affected_date": "2026-10-30",
          "record": { ... }
        }
      ],
      "recalculated_scores": {
        "2026-10-30": {
          "name": "SCORE-SARAH-2026-10-30",
          "score_date": "2026-10-30",
          "health_score": 84.5,
          "health_confidence": 75.0,
          "financial_score": 79.2,
          "financial_confidence": 70.0,
          "social_score": 80.0,
          "social_confidence": 85.0,
          "overall_score": 81.2,
          "scoring_version": "v1.0.0",
          "calculated_at": "2026-10-30 12:45:10"
        }
      }
    }
  }
}
```

##### Format B: Single Record Insert
```json
{
  "doctype": "Financial Transaction",
  "record_data": {
    "amount": 28.50,
    "category": "Pharmacy",
    "transaction_type": "Expense",
    "transaction_date": "2026-10-30"
  }
}
```
##### Single Record Response (HTTP 200):
```json
{
  "message": {
    "success": true,
    "message": "Financial Transaction created successfully",
    "name": "FT-00111",
    "doctype": "Financial Transaction",
    "affected_date": "2026-10-30",
    "data": {
      "name": "FT-00111",
      "user": "sarah.connor@example.com",
      "amount": 28.50,
      "category": "Pharmacy",
      "transaction_type": "Expense",
      "transaction_date": "2026-10-30"
    },
    "recalculated_score": {
      "health_score": 84.5,
      "financial_score": 78.4,
      "social_score": 80.0,
      "overall_score": 80.8
    }
  }
}
```

---

#### `store_ai_record`
Dedicated endpoint for LLMs, Voice transcripts, and AI agent output. Automatically maps domain keys (`health`, `financial`, `social`, `wellbeing`, `activity`) and injects `source: "AI Extraction"`.
- **URL**: `/api/method/well_pro.well_pro_app.api.store_ai_record`
- **Method**: `POST`
- **Auth**: Required

##### Multi-Domain Conversational Extraction Example:
*User says: "Hey, I slept 8 hours, walked 10,000 steps today, grabbed a $12 salad for lunch, and had a great dinner with my sister."*
```json
{
  "health": {
    "record_date": "2026-10-30",
    "steps": 10000,
    "sleep_hours": 8.0,
    "raw_input": "slept 8 hours, walked 10000 steps"
  },
  "financial": [
    {
      "amount": 12.00,
      "category": "Lunch",
      "transaction_type": "Expense",
      "raw_input": "grabbed a $12 salad for lunch"
    }
  ],
  "social": {
    "interaction_type": "In Person",
    "relationship_type": "Family",
    "interaction_quality": 5,
    "notes": "Great dinner with sister",
    "raw_input": "had a great dinner with my sister"
  }
}
```
##### Success Response (HTTP 200):
```json
{
  "message": {
    "success": true,
    "message": "Successfully processed 3 AI domain extractions",
    "data": {
      "count": 3,
      "affected_dates": ["2026-10-30"],
      "created": [ ... ],
      "recalculated_scores": {
        "2026-10-30": {
          "health_score": 88.0,
          "financial_score": 82.0,
          "social_score": 90.0,
          "overall_score": 86.4
        }
      }
    }
  }
}
```

---

### 5.3 Record Modification & Eviction Endpoints

#### `update_record`
Safely updates an existing user document. Recalculates scores for the original date and new date if the date changed.
- **URL**: `/api/method/well_pro.well_pro_app.api.update_record`
- **Method**: `POST`
- **Auth**: Required
- **Input JSON**:
```json
{
  "doctype": "Health Daily Record",
  "name": "HDR-00042",
  "update_data": {
    "water_liters": 3.0,
    "sleep_quality": 5
  }
}
```
- **Output JSON (HTTP 200)**:
```json
{
  "message": {
    "success": true,
    "message": "Health Daily Record updated successfully",
    "data": {
      "name": "HDR-00042",
      "water_liters": 3.0,
      "sleep_quality": 5
    }
  }
}
```

---

#### `delete_record`
Safely purges a record and updates daily scores.
- **URL**: `/api/method/well_pro.well_pro_app.api.delete_record`
- **Method**: `POST`
- **Auth**: Required
- **Input JSON**:
```json
{
  "doctype": "Financial Transaction",
  "name": "FT-00109"
}
```
- **Output JSON (HTTP 200)**:
```json
{
  "message": {
    "success": true,
    "message": "Financial Transaction deleted successfully",
    "data": {
      "doctype": "Financial Transaction",
      "name": "FT-00109"
    }
  }
}
```

---

### 5.4 Data Querying & Retrieval Endpoints

#### `get_user_records`
Paginated record retrieval scoped to the user.
- **URL**: `/api/method/well_pro.well_pro_app.api.get_user_records`
- **Method**: `GET` or `POST`
- **Auth**: Required
- **Query / Body Parameters**:
  - `doctype`: (e.g. `Financial Transaction`)
  - `limit`: (default `50`, max `200`)
  - `offset`: (default `0`)
  - `order_by`: (e.g. `transaction_date desc`)
  - `from_date`: `YYYY-MM-DD` (optional filter)
  - `to_date`: `YYYY-MM-DD` (optional filter)
- **Output JSON (HTTP 200)**:
```json
{
  "message": {
    "success": true,
    "data": [
      {
        "name": "FT-00110",
        "amount": 45.0,
        "category": "Groceries",
        "transaction_date": "2026-10-30"
      }
    ],
    "count": 1,
    "limit": 50,
    "offset": 0
  }
}
```

---

### 5.5 Dashboard & Score Analytics Endpoints

#### `get_dashboard_metrics` (Recommended for Primary Dashboard Screen)
Calculates current scores, multi-window trend summaries (7d, 30d, 90d), historical score timeline, and recent activity feeds.
- **URL**: `/api/method/well_pro.well_pro_app.api.get_dashboard_metrics`
- **Method**: `GET` or `POST`
- **Auth**: Required
- **Query / Body Parameters**:
  - `days`: Window in days for chart history (default `30`, min `1`, max `365`).
  - `as_of_date`: Target evaluation date (default `today()`).
- **Output JSON (HTTP 200)**:
```json
{
  "message": {
    "success": true,
    "message": "Dashboard metrics retrieved successfully",
    "data": {
      "as_of_date": "2026-10-30",
      "days": 30,
      "current_scores": {
        "name": "SCORE-SARAH-2026-10-30",
        "score_date": "2026-10-30",
        "health_score": 84.5,
        "health_confidence": 75.0,
        "financial_score": 79.2,
        "financial_confidence": 70.0,
        "social_score": 80.0,
        "social_confidence": 85.0,
        "overall_score": 81.2,
        "scoring_version": "v1.0.0"
      },
      "summary": {
        "health": {
          "today_score": 84.5,
          "current_score": 82.1,
          "confidence": 78.0,
          "seven_day_score": 83.0,
          "thirty_day_score": 82.1,
          "ninety_day_score": 80.5,
          "trend": "improving",
          "trend_change": 2.4
        },
        "financial": {
          "today_score": 79.2,
          "current_score": 77.0,
          "confidence": 72.0,
          "seven_day_score": 78.1,
          "thirty_day_score": 77.0,
          "ninety_day_score": 75.0,
          "trend": "stable",
          "trend_change": 0.5
        },
        "social": {
          "today_score": 80.0,
          "current_score": 79.5,
          "confidence": 80.0,
          "seven_day_score": 80.0,
          "thirty_day_score": 79.5,
          "ninety_day_score": 78.0,
          "trend": "improving",
          "trend_change": 1.2
        },
        "overall": {
          "today_score": 81.2,
          "score": 79.8,
          "seven_day_score": 80.5,
          "thirty_day_score": 79.8,
          "ninety_day_score": 78.1,
          "trend": "improving",
          "trend_change": 1.5
        }
      },
      "historical_trends": [
        {
          "score_date": "2026-10-28",
          "health_score": 80.0,
          "financial_score": 76.0,
          "social_score": 78.0,
          "overall_score": 78.2
        },
        {
          "score_date": "2026-10-29",
          "health_score": 82.0,
          "financial_score": 78.0,
          "social_score": 79.0,
          "overall_score": 79.8
        },
        {
          "score_date": "2026-10-30",
          "health_score": 84.5,
          "financial_score": 79.2,
          "social_score": 80.0,
          "overall_score": 81.2
        }
      ],
      "financial": [ ... recent 10 transactions ... ],
      "health": [ ... recent 10 daily records ... ],
      "health_activities": [ ... recent 10 activities ... ],
      "social": [ ... recent 10 social logs ... ],
      "checkins": [ ... recent 10 checkins ... ]
    }
  }
}
```

---

#### `recalculate_score`
Explicitly recalculates a score for a given date.
- **URL**: `/api/method/well_pro.well_pro_app.api.recalculate_score`
- **Method**: `POST`
- **Auth**: Required
- **Input JSON**:
```json
{
  "date": "2026-10-30"
}
```

---

### 5.6 Scoring Goals Configuration Endpoints

#### `setup_scoring_goals`
Customizes user wellbeing targets (e.g. 10k steps, $500 budget, 20% savings rate). Parses human-friendly strings like `"10k"`, `"20%"`, `"2500ml"`.
- **URL**: `/api/method/well_pro.well_pro_app.api.setup_scoring_goals`
- **Method**: `POST`
- **Auth**: Required
- **Input JSON**:
```json
{
  "goals": {
    "steps": "12k",
    "financial_budget": "$3,500",
    "savings_rate": "25%",
    "water": "3L",
    "exercise_minutes": 45
  },
  "recalculate": true
}
```
- **Output JSON (HTTP 200)**:
```json
{
  "message": {
    "success": true,
    "message": "Scoring goals updated and converted to config scale successfully",
    "data": {
      "configured_goals": {
        "steps_target": 12000,
        "budget_amount": 3500.0,
        "target_savings_rate": 0.25,
        "water_liters_target": 3.0,
        "exercise_minutes_target": 45
      },
      "recalculated_score": { ... }
    }
  }
}
```

---

#### `get_scoring_goals`
Retrieves effective user goals merged with system baseline heuristics.
- **URL**: `/api/method/well_pro.well_pro_app.api.get_scoring_goals`
- **Method**: `GET`
- **Auth**: Required

---

## 6. Frontend Integration Patterns (TypeScript / Axios)

### 6.1 Clean TypeScript API Client Implementation
```typescript
import axios, { AxiosInstance } from "axios";

export interface ApiResponse<T = any> {
  success: boolean;
  message: string;
  data: T;
  recalculated_score?: any;
}

export class WellProClient {
  private client: AxiosInstance;

  constructor(baseURL: string, apiKey?: string, apiSecret?: string) {
    this.client = axios.create({
      baseURL,
      headers: {
        "Content-Type": "application/json",
        ...(apiKey && apiSecret ? { Authorization: `token ${apiKey}:${apiSecret}` } : {})
      }
    });

    // Automatically unwrap Frappe's {"message": {...}} wrapper
    this.client.interceptors.response.use(
      (response) => response.data.message || response.data,
      (error) => {
        const errorData = error.response?.data;
        const msg = errorData?.message?.message || errorData?.exception || error.message;
        return Promise.reject(new Error(msg));
      }
    );
  }

  // 1. Ingestion: Single or Multi-DocType on a single request
  async insertRecord(payload: Record<string, any>): Promise<ApiResponse> {
    return this.client.post("/api/method/well_pro.well_pro_app.api.insert_record", payload);
  }

  // 2. Ingestion: AI / Voice multi-domain extraction
  async storeAiExtraction(payload: Record<string, any>): Promise<ApiResponse> {
    return this.client.post("/api/method/well_pro.well_pro_app.api.store_ai_record", payload);
  }

  // 3. Analytics: Dashboard metrics with historical trends
  async getDashboardMetrics(days: number = 30, asOfDate?: string): Promise<ApiResponse> {
    return this.client.get("/api/method/well_pro.well_pro_app.api.get_dashboard_metrics", {
      params: { days, as_of_date: asOfDate }
    });
  }

  // 4. Configuration: Set custom wellbeing goals
  async setGoals(goals: Record<string, any>): Promise<ApiResponse> {
    return this.client.post("/api/method/well_pro.well_pro_app.api.setup_scoring_goals", { goals });
  }
}
```

### 6.2 Example Usage in React / React Native:
```typescript
const api = new WellProClient("https://your-domain.com", "my_api_key", "my_api_secret");

// Multi-DocType Combined Daily Log
async function handleSaveDailyLog(values: any) {
  const res = await api.insertRecord({
    "Health Daily Record": {
      steps: values.steps,
      sleep_hours: values.sleepHours,
      sleep_quality: values.sleepQuality
    },
    "Financial Transaction": values.expenses.map((exp: any) => ({
      amount: exp.amount,
      category: exp.category,
      transaction_type: "Expense"
    })),
    "Social Activity": {
      activity_name: values.socialNote,
      interaction_quality: values.socialRating
    },
    "Subjective Wellbeing Checkin": {
      mood: values.moodRating,
      energy: values.energyRating
    }
  });

  console.log("Created docs:", res.data.created);
  console.log("Newly calculated daily score:", res.data.recalculated_scores);
}
```
