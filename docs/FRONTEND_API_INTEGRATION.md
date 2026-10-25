# WellPro Frontend API Integration Guide

This document contains a complete reference of all WellPro API endpoints, complete with **exact JSON request inputs**, **exact JSON response outputs**, and **TypeScript definitions** designed for direct frontend integration (React, Vue, Next.js, Flutter, React Native, etc.).

---

## 1. Quick Start & Protocol Guidelines

### 1.1 Base URL & Routing
All API calls are routed via Frappe RPC methods:
```
Base URL: http://<your-frappe-host>:8000/api/method/well_pro.well_pro_app.api.<method_name>
```

### 1.2 Authentication Header
For all protected endpoints, pass the user's `api_key` and `api_secret` (obtained from `/signup` or `/login`):
```http
Authorization: token <api_key>:<api_secret>
Content-Type: application/json
```

### 1.3 Response Wrapper Structure
Frappe wraps all whitelisted Python return values inside a top-level `{"message": ...}` key.
WellPro standardizes all responses into:
```json
{
  "message": {
    "success": true,
    "message": "Human-readable status message",
    "data": { ... }
  }
}
```
In your frontend Axios or Fetch interceptor:
```typescript
// With Axios
const data = response.data.message.data;
```

---

## 2. Authentication & Session Endpoints

### 2.1 User Signup (`signup`)
- **Method**: `POST`
- **Path**: `/api/method/well_pro.well_pro_app.api.signup`
- **Auth**: None (Guest allowed)

#### Request Input Example:
```json
{
  "email": "alex.doe@example.com",
  "password": "SecurePassword123!",
  "first_name": "Alex",
  "last_name": "Doe"
}
```

#### Success Response Output Example (HTTP 200):
```json
{
  "message": {
    "success": true,
    "message": "User registered successfully",
    "data": {
      "user": "alex.doe@example.com",
      "api_key": "4f9a8b1c2d3e4f5",
      "api_secret": "9a8b7c6d5e4f3a2b1c",
      "first_name": "Alex",
      "last_name": "Doe"
    }
  }
}
```

---

### 2.2 User Login (`login`)
- **Method**: `POST`
- **Path**: `/api/method/well_pro.well_pro_app.api.login`
- **Auth**: None (Guest allowed)

#### Request Input Example:
```json
{
  "usr": "alex.doe@example.com",
  "pwd": "SecurePassword123!"
}
```

#### Success Response Output Example (HTTP 200):
```json
{
  "message": {
    "success": true,
    "message": "Authentication successful",
    "data": {
      "user": "alex.doe@example.com",
      "api_key": "4f9a8b1c2d3e4f5",
      "api_secret": "9a8b7c6d5e4f3a2b1c"
    }
  }
}
```

---

### 2.3 Verify Session & Profile (`verify_user_session`)
- **Method**: `GET` or `POST`
- **Path**: `/api/method/well_pro.well_pro_app.api.verify_user_session`
- **Auth**: Required (`Authorization: token <api_key>:<api_secret>`)

#### Request Input:
*Empty body / No parameters required.*

#### Success Response Output Example (HTTP 200):
```json
{
  "message": {
    "success": true,
    "message": "Session valid",
    "data": {
      "user": "alex.doe@example.com",
      "profile": {
        "name": "alex.doe@example.com",
        "user": "alex.doe@example.com",
        "date_of_birth": "1995-06-15",
        "gender": "Non-Binary",
        "height_cm": 175.0,
        "baseline_weight_kg": 70.0,
        "timezone": "UTC"
      },
      "consent": {
        "name": "alex.doe@example.com",
        "user": "alex.doe@example.com",
        "health_tracking_enabled": 1,
        "financial_tracking_enabled": 1,
        "social_tracking_enabled": 1,
        "allow_ai_processing": 1,
        "consent_version": "v1.0"
      }
    }
  }
}
```

---

## 3. Data Insertion & Ingestion Endpoints

### 3.1 Generic Record Insert (`insert_record`)
- **Method**: `POST`
- **Path**: `/api/method/well_pro.well_pro_app.api.insert_record`
- **Auth**: Required
- **Behavior**:
  - Automatically ties record to authenticated user (`user = frappe.session.user`).
  - **Same-Day Accumulation**: Multiple Health Activities or Financial Transactions logged on the same date automatically accumulate into the daily summary records.
  - Automatically recalculates Wellbeing scores for the affected date.

---

#### 3.1.1 Health Daily Record Example
*Daily summary record covering sleep, nutrition, water, energy, and overall health.*

**Request Input:**
```json
{
  "doctype": "Health Daily Record",
  "record_data": {
    "record_date": "2026-10-25",
    "sleep_hours": 8.0,
    "sleep_quality": 4,
    "steps": 6000,
    "active_minutes": 30,
    "exercise_minutes": 30,
    "exercise_intensity": "Moderate",
    "water_liters": 2.5,
    "calories_consumed": 2100.0,
    "protein_grams": 75.0,
    "fruit_veg_servings": 5.0,
    "energy_level": 4,
    "self_rated_health": 4,
    "source": "Manual Entry"
  }
}
```

**Success Response Output (HTTP 200):**
```json
{
  "message": {
    "success": true,
    "message": "Health Daily Record created successfully",
    "data": {
      "name": "HLT-REC-2026-00001",
      "user": "alex.doe@example.com",
      "record_date": "2026-10-25",
      "sleep_hours": 8.0,
      "sleep_quality": 4,
      "steps": 6000,
      "active_minutes": 30,
      "exercise_minutes": 30,
      "exercise_intensity": "Moderate",
      "water_liters": 2.5,
      "calories_consumed": 2100.0,
      "protein_grams": 75.0,
      "fruit_veg_servings": 5.0,
      "energy_level": 4,
      "self_rated_health": 4,
      "source": "Manual Entry"
    }
  }
}
```

---

#### 3.1.2 Health Activity Example
*Individual workout / exercise session. Accumulates into Health Daily Record steps and exercise minutes.*

**Request Input:**
```json
{
  "doctype": "Health Activity",
  "record_data": {
    "activity_type": "Running",
    "logged_at": "2026-10-25 08:30:00",
    "duration_minutes": 35.0,
    "distance_km": 5.2,
    "steps": 4200,
    "calories_burned": 380.0,
    "intensity": "High",
    "source": "Wearable"
  }
}
```
*Note on `activity_type` options: `"Walking"`, `"Running"`, `"Cycling"`, `"Gym"`, `"Sports"`, `"Other"*  
*Note on `intensity` options: `"Low"`, `"Moderate"`, `"High"*

**Success Response Output (HTTP 200):**
```json
{
  "message": {
    "success": true,
    "message": "Health Activity created successfully",
    "data": {
      "name": "HEA-SNP-2026-10-00001",
      "user": "alex.doe@example.com",
      "activity_type": "Running",
      "logged_at": "2026-10-25 08:30:00",
      "duration_minutes": 35.0,
      "distance_km": 5.2,
      "steps": 4200,
      "calories_burned": 380.0,
      "intensity": "High",
      "source": "Wearable"
    }
  }
}
```

---

#### 3.1.3 Financial Transaction Example
*Individual income, expense, transfer, investment, or debt payment. Automatically accumulates into the daily Financial Snapshot.*

**Request Input (Expense):**
```json
{
  "doctype": "Financial Transaction",
  "record_data": {
    "transaction_type": "Expense",
    "category": "Groceries & Food",
    "amount": 78.50,
    "transaction_date": "2026-10-25",
    "merchant_or_source": "Trader Joe's",
    "description": "Weekly organic produce",
    "payment_method": "Card",
    "is_recurring": 0,
    "essentiality": "Essential",
    "source": "Manual Entry"
  }
}
```

**Request Input (Income):**
```json
{
  "doctype": "Financial Transaction",
  "record_data": {
    "transaction_type": "Income",
    "category": "Salary & Wages",
    "amount": 3500.00,
    "transaction_date": "2026-10-25",
    "merchant_or_source": "Employer Inc",
    "description": "Bi-weekly paycheck",
    "payment_method": "Bank",
    "is_recurring": 1,
    "essentiality": "Essential",
    "source": "Manual Entry"
  }
}
```
*Note on `transaction_type` options: `"Income"`, `"Expense"`, `"Transfer"`, `"Investment"`, `"Debt Payment"*  
*Note on `payment_method` options: `"Cash"`, `"Bank"`, `"Card"`, `"Digital Wallet"`, `"Other"*  
*Note on `essentiality` options: `"Essential"`, `"Discretionary"`, `"Not Applicable"*

**Success Response Output (HTTP 200):**
```json
{
  "message": {
    "success": true,
    "message": "Financial Transaction created successfully",
    "data": {
      "name": "FIN-TRA-2026-10-00001",
      "user": "alex.doe@example.com",
      "transaction_type": "Expense",
      "category": "Groceries & Food",
      "amount": 78.5,
      "transaction_date": "2026-10-25",
      "merchant_or_source": "Trader Joe's",
      "description": "Weekly organic produce",
      "payment_method": "Card",
      "is_recurring": 0,
      "essentiality": "Essential",
      "source": "Manual Entry"
    }
  }
}
```

---

#### 3.1.4 Financial Snapshot Example
*Monthly/periodic balance overview of income, expenses, liquid savings, investments, debt, and stress.*

**Request Input:**
```json
{
  "doctype": "Financial Snapshot",
  "record_data": {
    "snapshot_date": "2026-10-25",
    "monthly_income": 6500.0,
    "monthly_expenses": 3800.0,
    "essential_monthly_expenses": 2800.0,
    "liquid_savings": 15000.0,
    "investment_value": 25000.0,
    "emergency_fund": 18000.0,
    "budget_amount": 4200.0,
    "outstanding_debt": 5000.0,
    "monthly_debt_payment": 450.0,
    "financial_stress_rating": 2,
    "source": "Manual Entry"
  }
}
```

**Success Response Output (HTTP 200):**
```json
{
  "message": {
    "success": true,
    "message": "Financial Snapshot created successfully",
    "data": {
      "name": "FIN-SNP-2026-10-00001",
      "user": "alex.doe@example.com",
      "snapshot_date": "2026-10-25",
      "monthly_income": 6500.0,
      "monthly_expenses": 3800.0,
      "essential_monthly_expenses": 2800.0,
      "liquid_savings": 15000.0,
      "investment_value": 25000.0,
      "emergency_fund": 18000.0,
      "budget_amount": 4200.0,
      "outstanding_debt": 5000.0,
      "monthly_debt_payment": 450.0,
      "financial_stress_rating": 2,
      "source": "Manual Entry"
    }
  }
}
```

---

#### 3.1.5 Social Activity Example
*Social interaction sessions (dinner with friends, call with parents, community meetups).*

**Request Input:**
```json
{
  "doctype": "Social Activity",
  "record_data": {
    "logged_at": "2026-10-25 19:30:00",
    "interaction_type": "In Person",
    "relationship_type": "Friend",
    "duration_minutes": 90.0,
    "people_count": 3,
    "interaction_quality": 5,
    "connection_level": 5,
    "mood_after": 5,
    "notes": "Dinner and conversation with university friends",
    "source": "Manual Entry"
  }
}
```
*Note on `interaction_type` options: `"In Person"`, `"Call"`, `"Video Call"`, `"Messaging"`, `"Group Activity"`, `"Community Activity"`, `"Other"*  
*Ratings `interaction_quality`, `connection_level`, `mood_after` must be between `1` and `5`.*

**Success Response Output (HTTP 200):**
```json
{
  "message": {
    "success": true,
    "message": "Social Activity created successfully",
    "data": {
      "name": "SOC-ACT-2026-10-00001",
      "user": "alex.doe@example.com",
      "logged_at": "2026-10-25 19:30:00",
      "interaction_type": "In Person",
      "relationship_type": "Friend",
      "duration_minutes": 90.0,
      "interaction_quality": 5,
      "connection_level": 5,
      "mood_after": 5
    }
  }
}
```

---

#### 3.1.6 Subjective Wellbeing Checkin Example
*Daily evening mood, stress, energy, and subjective feelings.*

**Request Input:**
```json
{
  "doctype": "Subjective Wellbeing Checkin",
  "record_data": {
    "date": "2026-10-25",
    "mood": 4,
    "energy": 4,
    "stress": 2,
    "social_connection": 5,
    "loneliness": 1,
    "social_satisfaction": 5,
    "financial_stress": 2
  }
}
```
*All ratings must be integer ratings between `1` (lowest/least) and `5` (highest/most).*

**Success Response Output (HTTP 200):**
```json
{
  "message": {
    "success": true,
    "message": "Subjective Wellbeing Checkin created successfully",
    "data": {
      "name": "SUB-CHK-2026-10-00001",
      "user": "alex.doe@example.com",
      "date": "2026-10-25",
      "mood": 4,
      "energy": 4,
      "stress": 2,
      "social_connection": 5,
      "loneliness": 1,
      "social_satisfaction": 5,
      "financial_stress": 2
    }
  }
}
```

---

### 3.2 AI & Voice Ingestion (`store_ai_record`)
- **Method**: `POST`
- **Path**: `/api/method/well_pro.well_pro_app.api.store_ai_record`
- **Auth**: Required
- **Purpose**: Convenience endpoint for voice transcripts, OCR receipt scanning, or AI agents. Automatically resolves category links and enforces schema constraints.

#### Request Input Example (Financial Receipt OCR):
```json
{
  "domain": "financial",
  "record_data": {
    "transaction_type": "Expense",
    "category": "Dining & Social",
    "amount": 42.50,
    "transaction_date": "2026-10-25",
    "merchant_or_source": "Blue Bottle Coffee",
    "source": "OCR Receipt"
  }
}
```

#### Request Input Example (Voice Workout Extraction):
```json
{
  "domain": "health_activity",
  "record_data": {
    "activity_type": "Cycling",
    "logged_at": "2026-10-25 09:00:00",
    "duration_minutes": 45.0,
    "distance_km": 15.0,
    "intensity": "Moderate",
    "source": "Voice"
  }
}
```
*Allowed `domain` values: `"health"` (Health Daily Record), `"health_activity"` (Health Activity), `"financial"` (Financial Transaction), `"social"` (Social Activity), `"wellbeing"` (Subjective Checkin).*

#### Success Response Output (HTTP 200):
```json
{
  "message": {
    "success": true,
    "message": "Saved to Financial Transaction",
    "data": {
      "name": "FIN-TRA-2026-10-00002",
      "user": "alex.doe@example.com",
      "transaction_type": "Expense",
      "category": "Dining & Social",
      "amount": 42.5,
      "transaction_date": "2026-10-25",
      "merchant_or_source": "Blue Bottle Coffee",
      "source": "OCR Receipt"
    }
  }
}
```

---

## 4. Record Modification & Deletion Endpoints

### 4.1 Update Record (`update_record`)
- **Method**: `POST`
- **Path**: `/api/method/well_pro.well_pro_app.api.update_record`
- **Auth**: Required
- **Behavior**: Safely updates an existing document. Strips unauthorized protected fields (`user`, `owner`). Automatically recalculates the affected day's score.

#### Request Input Example:
```json
{
  "doctype": "Health Daily Record",
  "name": "HLT-REC-2026-00001",
  "update_data": {
    "steps": 11500,
    "active_minutes": 50,
    "water_liters": 3.0
  }
}
```

#### Success Response Output (HTTP 200):
```json
{
  "message": {
    "success": true,
    "message": "Health Daily Record updated successfully",
    "data": {
      "name": "HLT-REC-2026-00001",
      "user": "alex.doe@example.com",
      "record_date": "2026-10-25",
      "steps": 11500,
      "active_minutes": 50,
      "water_liters": 3.0
    }
  }
}
```

---

### 4.2 Delete Record (`delete_record`)
- **Method**: `POST`
- **Path**: `/api/method/well_pro.well_pro_app.api.delete_record`
- **Auth**: Required
- **Behavior**: Deletes caller's document and recalculates score for the affected date.

#### Request Input Example:
```json
{
  "doctype": "Health Activity",
  "name": "HEA-SNP-2026-10-00001"
}
```

#### Success Response Output (HTTP 200):
```json
{
  "message": {
    "success": true,
    "message": "Health Activity deleted successfully",
    "data": {
      "doctype": "Health Activity",
      "name": "HEA-SNP-2026-10-00001"
    }
  }
}
```

---

## 5. Retrieval, Scoring & Dashboard Endpoints

### 5.1 Paginated History Records (`get_user_records`)
- **Method**: `GET`
- **Path**: `/api/method/well_pro.well_pro_app.api.get_user_records`
- **Auth**: Required

#### Query Parameters:
| Parameter | Type | Required | Default | Description |
| :--- | :--- | :---: | :--- | :--- |
| `doctype` | string | **Yes** | - | Name of DocType (e.g. `"Financial Transaction"`) |
| `limit` | number | No | `50` | Records per page (max 200) |
| `offset` | number | No | `0` | Pagination start index |
| `order_by` | string | No | `"modified desc"` | SQL order clause (e.g. `"transaction_date desc"`) |
| `from_date` | string | No | `None` | Filter start date (`YYYY-MM-DD`) |
| `to_date` | string | No | `None` | Filter end date (`YYYY-MM-DD`) |

#### Request Example (URL):
```
GET /api/method/well_pro.well_pro_app.api.get_user_records?doctype=Financial Transaction&limit=2&from_date=2026-10-01&to_date=2026-10-25
```

#### Success Response Output (HTTP 200):
```json
{
  "message": {
    "success": true,
    "message": "Success",
    "data": [
      {
        "name": "FIN-TRA-2026-10-00002",
        "user": "alex.doe@example.com",
        "transaction_type": "Expense",
        "category": "Dining & Social",
        "amount": 42.5,
        "transaction_date": "2026-10-25",
        "merchant_or_source": "Blue Bottle Coffee",
        "essentiality": "Discretionary"
      },
      {
        "name": "FIN-TRA-2026-10-00001",
        "user": "alex.doe@example.com",
        "transaction_type": "Expense",
        "category": "Groceries & Food",
        "amount": 78.5,
        "transaction_date": "2026-10-25",
        "merchant_or_source": "Trader Joe's",
        "essentiality": "Essential"
      }
    ],
    "count": 2,
    "limit": 2,
    "offset": 0
  }
}
```

---

### 5.2 Explicit Score Recalculation (`recalculate_score`)
- **Method**: `POST`
- **Path**: `/api/method/well_pro.well_pro_app.api.recalculate_score`
- **Auth**: Required
- **Purpose**: Explicitly forces re-accumulation and recalculation of Health, Financial, Social, and Composite Wellbeing scores for a given day.

#### Request Input Example:
```json
{
  "date": "2026-10-25"
}
```
*(If `date` is omitted, defaults to today's date).*

#### Success Response Output (HTTP 200):
```json
{
  "message": {
    "success": true,
    "message": "Wellbeing score for 2026-10-25 calculated successfully",
    "data": {
      "name": "SCORE-ALEX-DOE-2026-10-25",
      "user": "alex.doe@example.com",
      "score_date": "2026-10-25",
      "health_score": 92.4,
      "health_confidence": 95.0,
      "financial_score": 85.0,
      "financial_confidence": 100.0,
      "social_score": 88.0,
      "social_confidence": 85.0,
      "overall_score": 88.7,
      "scoring_version": "v1",
      "calculated_at": "2026-10-25 10:15:30.123456"
    }
  }
}
```

---

### 5.3 Complete Wellbeing Dashboard (`get_dashboard`)
- **Method**: `GET`
- **Path**: `/api/method/well_pro.well_pro_app.api.get_dashboard`
- **Auth**: Required
- **Purpose**: Primary endpoint for mobile & web dashboard screens. Automatically refreshes today's score and computes **7-day, 30-day, and 90-day exponential recency-weighted scores**, **completeness confidences**, and **trend velocity (improving, stable, declining)**.

#### Query Parameters:
| Parameter | Type | Required | Default | Description |
| :--- | :--- | :---: | :--- | :--- |
| `as_of_date` | string | No | `today` (`YYYY-MM-DD`) | Reference date for calculations |

#### Request Example (URL):
```
GET /api/method/well_pro.well_pro_app.api.get_dashboard?as_of_date=2026-10-25
```

#### Success Response Output (HTTP 200):
```json
{
  "message": {
    "success": true,
    "message": "Dashboard metrics retrieved successfully",
    "data": {
      "health": {
        "today_score": 92.4,
        "current_score": 86.5,
        "confidence": 95.0,
        "seven_day_score": 89.2,
        "thirty_day_score": 86.5,
        "ninety_day_score": 82.1,
        "trend": "improving",
        "trend_change": 5.4
      },
      "financial": {
        "today_score": 85.0,
        "current_score": 81.3,
        "confidence": 100.0,
        "seven_day_score": 83.0,
        "thirty_day_score": 81.3,
        "ninety_day_score": 79.0,
        "trend": "stable",
        "trend_change": 1.2
      },
      "social": {
        "today_score": 88.0,
        "current_score": 83.2,
        "confidence": 85.0,
        "seven_day_score": 86.0,
        "thirty_day_score": 83.2,
        "ninety_day_score": 80.5,
        "trend": "improving",
        "trend_change": 4.8
      },
      "overall": {
        "score": 84.1,
        "today_score": 88.7,
        "seven_day_score": 86.4,
        "thirty_day_score": 84.1,
        "ninety_day_score": 80.8,
        "trend": "improving",
        "trend_change": 4.5
      },
      "scoring_version": "v1",
      "as_of_date": "2026-10-25"
    }
  }
}
```

---

## 6. Frontend TypeScript SDK & Service Client Example

Here is a ready-to-use TypeScript service file for your frontend application:

```typescript
// services/wellproApi.ts
import axios, { AxiosInstance } from 'axios';

export interface WellProConfig {
  baseUrl: string;
  apiKey?: string;
  apiSecret?: string;
}

export interface DomainMetric {
  today_score: number | null;
  current_score: number | null;
  confidence: number;
  seven_day_score: number | null;
  thirty_day_score: number | null;
  ninety_day_score: number | null;
  trend: 'improving' | 'stable' | 'declining';
  trend_change: number;
}

export interface DashboardResponse {
  health: DomainMetric;
  financial: DomainMetric;
  social: DomainMetric;
  overall: {
    score: number | null;
    today_score: number | null;
    seven_day_score: number | null;
    thirty_day_score: number | null;
    ninety_day_score: number | null;
    trend: 'improving' | 'stable' | 'declining';
    trend_change: number;
  };
  scoring_version: string;
  as_of_date: string;
}

export class WellProClient {
  private client: AxiosInstance;

  constructor(config: WellProConfig) {
    this.client = axios.create({
      baseURL: `${config.baseUrl}/api/method/well_pro.well_pro_app.api`,
      headers: {
        'Content-Type': 'application/json',
        ...(config.apiKey && config.apiSecret
          ? { Authorization: `token ${config.apiKey}:${config.apiSecret}` }
          : {}),
      },
    });

    // Unpack Frappe {"message": { ... }} response automatically
    this.client.interceptors.response.use((res) => {
      if (res.data && res.data.message) {
        return res.data.message;
      }
      return res.data;
    });
  }

  // Auth
  async signup(payload: { email: string; password: string; first_name: string; last_name?: string }) {
    return this.client.post('/signup', payload);
  }

  async login(payload: { usr: string; pwd: string }) {
    return this.client.post('/login', payload);
  }

  async verifySession() {
    return this.client.get('/verify_user_session');
  }

  // Dashboard
  async getDashboard(asOfDate?: string): Promise<{ success: boolean; data: DashboardResponse }> {
    return this.client.get('/get_dashboard', { params: { as_of_date: asOfDate } });
  }

  // Recalculate Score
  async recalculateScore(date?: string) {
    return this.client.post('/recalculate_score', { date });
  }

  // Ingest Records
  async insertRecord(doctype: string, recordData: Record<string, any>) {
    return this.client.post('/insert_record', { doctype, record_data: recordData });
  }

  // History Query
  async getRecords(doctype: string, options?: { limit?: number; offset?: number; from_date?: string; to_date?: string }) {
    return this.client.get('/get_user_records', { params: { doctype, ...options } });
  }
}
```
