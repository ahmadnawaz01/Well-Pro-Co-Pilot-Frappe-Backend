# WellPro DocType Schema & Agent Tool Calling Guide

This document is the authoritative schema reference for **AI Agents, LLMs, and API Clients** that interact with the WellPro backend. It provides exact field names, data types, required constraints, allowed enumeration values, validation rules, and sample JSON payloads for every DocType.

---

## 1. Agent Tool Calling Instructions

When configuring an AI Agent with document insertion tools, provide this section as the operational system prompt.

### 1.1 Available Tool Endpoints
The agent can persist extracted data using either of two endpoints:

1. **`insert_record(doctype, record_data)`** *(Generic Tool)*:
   - Accepts the explicit Frappe `doctype` name.
   - Example: `insert_record("Health Daily Record", {...})`
2. **`store_ai_record(domain, record_data)`** *(High-Level Domain Tool)*:
   - Maps simplified domains to the appropriate DocType automatically:
     - `"health"` $\rightarrow$ `Health Daily Record`
     - `"health_activity"` $\rightarrow$ `Health Activity`
     - `"financial"` $\rightarrow$ `Financial Transaction`
     - `"social"` $\rightarrow$ `Social Activity`
     - `"wellbeing"` $\rightarrow$ `Subjective Wellbeing Checkin`

### 1.2 Critical Rules for Agents
1. **Do NOT generate System Fields**: Never include `name`, `owner`, `creation`, `modified_by`, `docstatus`, or `idx`. The server manages these.
2. **Do NOT supply `user`**: The authenticated caller identity (`frappe.session.user`) is injected authoritatively by the server. Even if supplied, it is overwritten.
3. **Date & Time Formats**:
   - `Date` fields: strictly `YYYY-MM-DD` (e.g., `"2026-10-23"`).
   - `Datetime` fields: strictly `YYYY-MM-DD HH:MM:SS` (e.g., `"2026-10-23 18:30:00"`).
4. **Rating Bounds**: Any rating field (`mood`, `stress`, `loneliness`, `energy`, `quality`, etc.) **MUST** be an integer between `1` and `5`. Values outside 1–5 will fail server-side validation.
5. **Positive Numbers**: Transaction `amount` must be greater than zero (`amount > 0`). Durations, steps, milliliters/liters, grams, and asset amounts cannot be negative (`>= 0`).
6. **No Duplicate Daily Records**: A user can only have **one** `Health Daily Record` and **one** `Subjective Wellbeing Checkin` per calendar date. If multiple logs occur on the same day, update the existing record or log discrete events as `Health Activity` or `Social Activity`.

---

## 2. DocType Schemas & JSON Specifications

---

### 2.1 `Health Daily Record`
* **Domain Key**: `"health"`
* **Purpose**: Aggregated daily health metrics for one calendar day (sleep, nutrition, hydration, daily steps, self-rating).

#### Fields Table
| Fieldname | Fieldtype | Req? | Allowed Values / Options | Default | Description & Constraints |
| :--- | :--- | :---: | :--- | :---: | :--- |
| `record_date` | `Date` | **Yes** | `YYYY-MM-DD` | None | Target day (Unique per user). |
| `sleep_hours` | `Float` | No | Any positive float | None | Total hours slept (optimal: 7.0–9.0). Must be $\ge 0$. |
| `sleep_quality` | `Int` | No | `1`, `2`, `3`, `4`, `5` | None | Subjective sleep rating (1 = terrible, 5 = excellent). |
| `steps` | `Int` | No | Any positive integer | None | Total daily steps counted. Must be $\ge 0$. |
| `active_minutes` | `Int` | No | Any positive integer | None | Minutes of moderate/brisk activity. Must be $\ge 0$. |
| `exercise_minutes`| `Int` | No | Any positive integer | None | Dedicated workout minutes. Must be $\ge 0$. |
| `exercise_intensity`| `Select`| No | `Low`, `Moderate`, `High` | None | Dominant workout intensity. |
| `water_liters` | `Float` | No | Any positive float | None | Total water intake in liters (target: 2.5L). Must be $\ge 0$. |
| `calories_consumed`|`Float` | No | Any positive float | None | Total calories eaten (optimal: 1800–2500). Must be $\ge 0$. |
| `protein_grams` | `Float` | No | Any positive float | None | Protein intake in grams. Must be $\ge 0$. |
| `fruit_veg_servings`|`Float` | No | Any positive float | None | Number of vegetable and fruit portions. Must be $\ge 0$. |
| `energy_level` | `Int` | No | `1`, `2`, `3`, `4`, `5` | None | Daily physical energy rating (1 = exhausted, 5 = peak). |
| `self_rated_health`| `Int` | No | `1`, `2`, `3`, `4`, `5` | None | Overall health perception (1 = very poor, 5 = excellent). |
| `source` | `Select`| No | `Manual Entry`, `Voice`, `Wearable`, `AI Extraction`, `Import`, `Other` | `Manual Entry` | Data ingestion channel. |

#### Agent Output Payload Example
```json
{
  "doctype": "Health Daily Record",
  "record_data": {
    "record_date": "2026-10-23",
    "sleep_hours": 7.8,
    "sleep_quality": 4,
    "steps": 10240,
    "active_minutes": 45,
    "exercise_minutes": 30,
    "exercise_intensity": "Moderate",
    "water_liters": 2.6,
    "calories_consumed": 2150.0,
    "protein_grams": 75.0,
    "fruit_veg_servings": 5.0,
    "energy_level": 4,
    "self_rated_health": 4,
    "source": "AI Extraction"
  }
}
```

---

### 2.2 `Health Activity`
* **Domain Key**: `"health_activity"`
* **Purpose**: Discrete physical workout session or sport activity (multiple logs allowed per day).

#### Fields Table
| Fieldname | Fieldtype | Req? | Allowed Values / Options | Default | Description & Constraints |
| :--- | :--- | :---: | :--- | :---: | :--- |
| `activity_type` | `Select` | **Yes** | `Walking`, `Running`, `Cycling`, `Gym`, `Sports`, `Other` | None | Category of workout. |
| `logged_at` | `Datetime` | **Yes** | `YYYY-MM-DD HH:MM:SS` | `Now` | Date and time the session occurred. |
| `duration_minutes` | `Float` | No | Positive float | None | Duration in minutes. Must be $\ge 0$. |
| `distance_km` | `Float` | No | Positive float | None | Distance covered in kilometers. Must be $\ge 0$. |
| `steps` | `Int` | No | Positive integer | None | Steps accumulated during this activity. Must be $\ge 0$. |
| `calories_burned` | `Float` | No | Positive float | None | Estimated calories burned. Must be $\ge 0$. |
| `intensity` | `Select` | No | `Low`, `Moderate`, `High` | None | Perceived workout exertion. |
| `source` | `Select` | No | `Manual Entry`, `Voice`, `Wearable`, `AI Extraction`, `Other` | `Manual Entry` | Input source. |
| `raw_input` | `Text` | No | Any text | None | Raw user transcript, voice dictation, or watch payload. |

#### Agent Output Payload Example
```json
{
  "doctype": "Health Activity",
  "record_data": {
    "activity_type": "Running",
    "logged_at": "2026-10-23 07:30:00",
    "duration_minutes": 42.0,
    "distance_km": 6.2,
    "steps": 5400,
    "calories_burned": 440.0,
    "intensity": "High",
    "source": "Voice",
    "raw_input": "I ran 6.2 kilometers in about 42 minutes around the park this morning."
  }
}
```

---

### 2.3 `Financial Transaction`
* **Domain Key**: `"financial"`
* **Purpose**: Individual financial ledger entry (income, expense, transfer, investment, debt payment).

#### Fields Table
| Fieldname | Fieldtype | Req? | Allowed Values / Options | Default | Description & Constraints |
| :--- | :--- | :---: | :--- | :---: | :--- |
| `transaction_type`| `Select` | **Yes** | `Income`, `Expense`, `Transfer`, `Investment`, `Debt Payment` | None | Nature of financial movement. |
| `category` | `Link` | **Yes** | Must link to a `Financial Category` | None | Category name (e.g. `"Groceries & Food"`, `"Salary & Wages"`). |
| `amount` | `Currency`| **Yes** | Positive float $> 0$ | None | Monetary value. **Must be strictly positive**. |
| `transaction_date`| `Date` | **Yes** | `YYYY-MM-DD` | `Today` | Date the transaction took place. |
| `merchant_or_source`|`Data` | No | Up to 140 chars | None | Store name, employer, or payee (e.g. `"Trader Joe's"`). |
| `description` | `Small Text`| No | Descriptive string | None | Itemized details or context. |
| `payment_method` | `Select` | No | `Cash`, `Bank`, `Card`, `Digital Wallet`, `Other` | None | Method of payment. |
| `is_recurring` | `Check` | No | `0` or `1` | `0` | `1` if monthly recurring bill/salary, otherwise `0`. |
| `essentiality` | `Select` | No | `Essential`, `Discretionary`, `Not Applicable` | `Discretionary`| Need vs want classification. |
| `source` | `Select` | No | `Manual Entry`, `Voice`, `OCR Receipt`, `AI Extraction`, `Import`, `Bank Integration`, `Other` | `Manual Entry` | Channel. |
| `raw_input` | `Text` | No | Raw text or OCR scan | None | Scanned receipt text or voice dictation. |

#### Agent Output Payload Example (Receipt OCR Extraction)
```json
{
  "doctype": "Financial Transaction",
  "record_data": {
    "transaction_type": "Expense",
    "category": "Groceries & Food",
    "amount": 64.35,
    "transaction_date": "2026-10-23",
    "merchant_or_source": "Whole Foods Market",
    "description": "Weekly fresh vegetables, almond milk, and eggs",
    "payment_method": "Card",
    "essentiality": "Essential",
    "is_recurring": 0,
    "source": "OCR Receipt",
    "raw_input": "WHOLE FOODS #1042 TOTAL: $64.35 VISA ENDING IN 4012"
  }
}
```

---

### 2.4 `Financial Snapshot`
* **Domain Key**: N/A (Inserted via generic `insert_record`)
* **Purpose**: Periodic (e.g. monthly) balance sheet and liquid wealth snapshot.

#### Fields Table
| Fieldname | Fieldtype | Req? | Allowed Values / Options | Default | Description & Constraints |
| :--- | :--- | :---: | :--- | :---: | :--- |
| `snapshot_date` | `Date` | **Yes** | `YYYY-MM-DD` | None | Date of balance sheet record. |
| `monthly_income` | `Currency`| No | Float $\ge 0$ | None | Total monthly net income. |
| `monthly_expenses`| `Currency`| No | Float $\ge 0$ | None | Total estimated monthly expenses. |
| `essential_monthly_expenses`| `Currency`| No | Float $\ge 0$ | None | Core survival expenses (rent, food, healthcare). |
| `liquid_savings` | `Currency`| No | Float $\ge 0$ | None | Cash in checking / instant savings. |
| `investment_value`| `Currency`| No | Float $\ge 0$ | None | Portfolio value in stocks, retirement, crypto. |
| `emergency_fund` | `Currency`| No | Float $\ge 0$ | None | Dedicated liquid emergency reserve. |
| `budget_amount` | `Currency`| No | Float $\ge 0$ | None | Monthly spending cap target. |
| `outstanding_debt`| `Currency`| No | Float $\ge 0$ | None | Total balance of loans, credit cards, mortgages. |
| `monthly_debt_payment`|`Currency`|No | Float $\ge 0$ | None | Total monthly debt service. |
| `financial_stress_rating`|`Int`| No | `1`, `2`, `3`, `4`, `5` | None | 1 = Calm / no stress, 5 = Severe anxiety. |
| `source` | `Select` | No | `Manual Entry`, `Import`, `Calculated` | `Manual Entry` | Origin. |

#### Agent Output Payload Example
```json
{
  "doctype": "Financial Snapshot",
  "record_data": {
    "snapshot_date": "2026-10-23",
    "monthly_income": 6800.0,
    "monthly_expenses": 4100.0,
    "essential_monthly_expenses": 2800.0,
    "liquid_savings": 24000.0,
    "investment_value": 42000.0,
    "emergency_fund": 20000.0,
    "budget_amount": 4200.0,
    "outstanding_debt": 5200.0,
    "monthly_debt_payment": 450.0,
    "financial_stress_rating": 2,
    "source": "Manual Entry"
  }
}
```

---

### 2.5 `Social Activity`
* **Domain Key**: `"social"`
* **Purpose**: Discrete social interaction log (conversation, meal, call, gathering). Multiple logs permitted per day.

#### Fields Table
| Fieldname | Fieldtype | Req? | Allowed Values / Options | Default | Description & Constraints |
| :--- | :--- | :---: | :--- | :---: | :--- |
| `logged_at` | `Datetime` | **Yes** | `YYYY-MM-DD HH:MM:SS` | `Now` | Date and time interaction took place. |
| `interaction_type`| `Select` | **Yes** | `In Person`, `Call`, `Video Call`, `Messaging`, `Group Activity`, `Community Activity`, `Other` | None | Interaction mode. |
| `relationship_type`| `Select`| **Yes** | `Family`, `Friend`, `Partner`, `Colleague`, `Community`, `Other` | None | Relationship to counterpart. |
| `duration_minutes`| `Float` | No | Float $\ge 0$ | None | Duration in minutes. Must be $\ge 0$. |
| `interaction_quality`| `Int`| No | `1`, `2`, `3`, `4`, `5` | None | Quality of engagement (1 = poor/awkward, 5 = deeply fulfilling). |
| `connection_level`| `Int` | No | `1`, `2`, `3`, `4`, `5` | None | Feeling of intimacy/bond (1 = distant, 5 = deeply bonded). |
| `mood_after` | `Int` | No | `1`, `2`, `3`, `4`, `5` | None | Mood following interaction (1 = drained/sad, 5 = energized/happy). |
| `notes` | `Small Text`| No | String | None | Key topics or emotional takeaways. |
| `source` | `Select` | No | `Manual Entry`, `Voice`, `AI Extraction`, `Import`, `Other` | `Manual Entry` | Channel. |
| `raw_input` | `Text` | No | String | None | Voice transcript or reflection. |

#### Agent Output Payload Example
```json
{
  "doctype": "Social Activity",
  "record_data": {
    "logged_at": "2026-10-23 19:30:00",
    "interaction_type": "In Person",
    "relationship_type": "Friend",
    "duration_minutes": 90.0,
    "interaction_quality": 5,
    "connection_level": 5,
    "mood_after": 5,
    "notes": "Caught up with Alex over coffee; discussed career plans and shared book recommendations.",
    "source": "Voice",
    "raw_input": "I had coffee with Alex for an hour and a half. It felt great to reconnect and catch up."
  }
}
```

---

### 2.6 `Subjective Wellbeing Checkin`
* **Domain Key**: `"wellbeing"`
* **Purpose**: Daily evening reflection capturing emotional state, stress, and connection. Exactly one record per user per date.

#### Fields Table
| Fieldname | Fieldtype | Req? | Allowed Values / Options | Default | Description & Constraints |
| :--- | :--- | :---: | :--- | :---: | :--- |
| `date` | `Date` | **Yes** | `YYYY-MM-DD` | `Today` | Calendar date (Unique per user). |
| `mood` | `Int` | No | `1`, `2`, `3`, `4`, `5` | None | Overall mood (1 = very low/depressed, 5 = radiant/joyful). |
| `energy` | `Int` | No | `1`, `2`, `3`, `4`, `5` | None | Mental/vitality energy (1 = burnt out, 5 = vibrant). |
| `stress` | `Int` | No | `1`, `2`, `3`, `4`, `5` | None | Stress level (1 = peaceful/relaxed, 5 = overwhelming). |
| `social_connection`|`Int`| No | `1`, `2`, `3`, `4`, `5` | None | Feeling connected to others (1 = isolated, 5 = supported). |
| `loneliness` | `Int` | No | `1`, `2`, `3`, `4`, `5` | None | Feeling lonely (**1 = not lonely at all, 5 = intensely lonely**). |
| `social_satisfaction`|`Int`|No | `1`, `2`, `3`, `4`, `5` | None | Satisfaction with social life (1 = unsatisfied, 5 = completely fulfilled). |
| `financial_stress`|`Int` | No | `1`, `2`, `3`, `4`, `5` | None | Financial worry (1 = totally secure, 5 = severe panic). |

#### Agent Output Payload Example
```json
{
  "doctype": "Subjective Wellbeing Checkin",
  "record_data": {
    "date": "2026-10-23",
    "mood": 4,
    "energy": 4,
    "stress": 2,
    "social_connection": 4,
    "loneliness": 1,
    "social_satisfaction": 4,
    "financial_stress": 1
  }
}
```

---

### 2.7 `Financial Category`
* **Domain Key**: N/A (System Reference Data)
* **Purpose**: Master classification table for transactions. Normal users have **read-only** access.

#### Fields Table
| Fieldname | Fieldtype | Req? | Allowed Values / Options | Default | Description & Constraints |
| :--- | :--- | :---: | :--- | :---: | :--- |
| `category_name` | `Data` | **Yes** | String (Unique) | None | Name (e.g. `"Groceries & Food"`). |
| `category_type` | `Select` | **Yes** | `Income`, `Expense`, `Investment`, `Debt`, `Transfer` | None | Primary category classification. |
| `active` | `Check` | No | `0` or `1` | `1` | Whether active for selection. |
| `description` | `Small Text`| No | String | None | Description of expenses in this category. |

---

### 2.8 `User Consent Preference`
* **Purpose**: User privacy switches and permission preferences. Automatically created upon signup.

#### Fields Table
| Fieldname | Fieldtype | Req? | Options / Default | Description |
| :--- | :--- | :---: | :---: | :--- |
| `user` | `Link: User` | **Yes** | Unique | Owner user. |
| `health_tracking_enabled` | `Check` | No | Default: `1` | Health feature toggle. |
| `financial_tracking_enabled` | `Check` | No | Default: `1` | Financial feature toggle. |
| `social_tracking_enabled` | `Check` | No | Default: `1` | Social feature toggle. |
| `allow_ai_processing` | `Check` | No | Default: `0` | Global AI processing consent. |
| `allow_voice_processing` | `Check` | No | Default: `0` | Speech-to-text consent. |
| `allow_image_processing` | `Check` | No | Default: `0` | Photo receipt processing consent. |
| `allow_document_ocr` | `Check` | No | Default: `0` | Document parsing consent. |
| `allow_health_ai_processing` | `Check` | No | Default: `0` | Health data AI consent. |
| `allow_financial_ai_processing` | `Check` | No | Default: `0` | Financial data AI consent. |
| `consent_version` | `Data` | No | Default: `v1.0`| Version of legal terms agreed. |

---

### 2.9 `WellPro Profile`
* **Purpose**: Physical and localization settings. Automatically created upon signup.

#### Fields Table
| Fieldname | Fieldtype | Req? | Options / Default | Description |
| :--- | :--- | :---: | :---: | :--- |
| `user` | `Link: User` | **Yes** | Unique | Owner user. |
| `date_of_birth` | `Date` | No | `YYYY-MM-DD` | Used for age-adjusted heuristics. |
| `timezone` | `Data` | No | e.g. `"UTC"`, `"Asia/Karachi"` | User's local timezone. |
| `preferred_currency` | `Link: Currency` | No | e.g. `"USD"`, `"PKR"` | Default currency for financial metrics. |
| `height_cm` | `Float` | No | Float $> 0$ | Height in cm. |
| `health_tracking_enabled` | `Check` | No | Default: `1` | Active health tracking. |
| `financial_tracking_enabled`| `Check` | No | Default: `1` | Active financial tracking. |
| `social_tracking_enabled` | `Check` | No | Default: `1` | Active social tracking. |

---

### 2.10 `Wellbeing Daily Score` *(Read-Only for Agents)*
* **Purpose**: Output of the backend scoring engine. Generated automatically by background tasks or after CRUD operations. Agents should **not** insert or update this table directly.

#### Fields Table
| Fieldname | Fieldtype | Description |
| :--- | :--- | :--- |
| `score_date` | `Date` | Calendar date evaluated. |
| `health_score` | `Float` | Health category score ($0.0 - 100.0$). |
| `health_confidence` | `Float` | Completeness of health metrics ($0.0 - 100.0\%$). |
| `financial_score` | `Float` | Financial category score ($0.0 - 100.0$). |
| `financial_confidence`| `Float` | Completeness of financial metrics ($0.0 - 100.0\%$). |
| `social_score` | `Float` | Social category score ($0.0 - 100.0$). |
| `social_confidence` | `Float` | Completeness of social metrics ($0.0 - 100.0\%$). |
| `overall_score` | `Float` | Weighted blended overall score ($0.0 - 100.0$). |
| `scoring_version` | `Data` | Algorithm version (e.g. `"v1"`). |
| `calculated_at` | `Datetime`| Timestamp calculation occurred. |

---

## 3. Agent Tool Call Extraction Guide

Here are prompt patterns showing how an LLM agent should map user inputs into structured tool calls:

### Scenario A: Wearable Sync / Morning Health Journal
**User Input**: *"I slept about 7 and a half hours last night, woke up feeling pretty good maybe 4 out of 5. Did 8,500 steps today and drank 2 liters of water."*  
**Agent Tool Call**:
```json
{
  "tool": "insert_record",
  "arguments": {
    "doctype": "Health Daily Record",
    "record_data": {
      "record_date": "2026-10-23",
      "sleep_hours": 7.5,
      "sleep_quality": 4,
      "steps": 8500,
      "water_liters": 2.0,
      "energy_level": 4,
      "source": "Voice"
    }
  }
}
```

### Scenario B: Receipt / OCR Ingestion
**User Input**: *"Here is my grocery receipt from yesterday at Fresh Mart for $82.40 on my debit card."*  
**Agent Tool Call**:
```json
{
  "tool": "insert_record",
  "arguments": {
    "doctype": "Financial Transaction",
    "record_data": {
      "transaction_type": "Expense",
      "category": "Groceries & Food",
      "amount": 82.40,
      "transaction_date": "2026-10-22",
      "merchant_or_source": "Fresh Mart",
      "payment_method": "Card",
      "essentiality": "Essential",
      "source": "OCR Receipt"
    }
  }
}
```

### Scenario C: Evening Mood Check-In
**User Input**: *"Today was calm. Mood was a solid 4, stress was low around 2. Had dinner with family so felt connected around 5 and not lonely at all."*  
**Agent Tool Call**:
```json
{
  "tool": "insert_record",
  "arguments": {
    "doctype": "Subjective Wellbeing Checkin",
    "record_data": {
      "date": "2026-10-23",
      "mood": 4,
      "energy": 4,
      "stress": 2,
      "social_connection": 5,
      "loneliness": 1,
      "social_satisfaction": 4
    }
  }
}
```
