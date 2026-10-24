# WellPro Wellbeing Scoring Engine Specification (Version 1)

**Package**: `well_pro.well_pro_app.services.scoring`  
**Current Version**: `v1`  
**Scale**: `0.0 – 100.0`

---

## 1. Principles & Architecture

The WellPro scoring engine implements a strictly layered data pipeline that decouples source recording from analytics and user presentation:

```
RAW FRAFFE DOCTYPES
(Health Daily Record, Financial Snapshot, Social Activity, Checkin)
                      ↓
           METRIC NORMALIZATION (0–100)
(Higher-is-better, Target-range, Rating, Inverse-rating)
                      ↓
         DAILY DOMAIN SCORES & CONFIDENCES
 (Health 0-100, Financial 0-100, Social 0-100)
                      ↓
           WEIGHT RENORMALIZATION
       (Exclude missing metrics without penalty)
                      ↓
          OVERALL DAILY WELLBEING SCORE
        (Health 40%, Financial 35%, Social 25%)
                      ↓
   HISTORICAL EXPONENTIAL RECENCY WEIGHTING
       (Half-life: 14 days, Windows: 7/30/90 days)
                      ↓
                 TREND ENGINE
   (Recent 7d vs Previous 7d: Improving / Declining / Stable)
                      ↓
             DASHBOARD CONSUMER
```

### Why 0–100?
A bounded 0–100 continuous float provides an intuitive percentage-like scale for users and frontend dashboards while enabling mathematical consistency across vastly different dimensions (e.g. sleep hours vs currency ratios vs 1-5 mood ratings).

### Important Disclaimer
> **Disclaimer**: Health, financial, and social thresholds implemented in this scoring engine are **wellbeing heuristics** designed for personal awareness and holistic habit tracking. They do **not** constitute medical diagnosis, clinical advice, credit underwriting, or certified financial planning.

---

## 2. Metric Normalization Strategies

Every raw metric is mapped to 0.0–100.0 through reusable normalizers defined in `well_pro.well_pro_app.services.scoring.normalization`. Every normalizer handles `None`, prevents division by zero, and clamps output strictly to `[0.0, 100.0]`.

### 2.1 Higher-Is-Better (`HIGHER_IS_BETTER`)
Used for progress toward a positive goal (steps, exercise minutes, water, emergency fund coverage).
$$\text{score} = \min\left(\frac{\text{value}}{\text{target}}, 1.0\right) \times 100$$
- Example: 7,500 steps toward a 10,000 target $\rightarrow 75.0$
- Example: 15,000 steps toward a 10,000 target $\rightarrow 100.0$ (capped)

### 2.2 Lower-Is-Better (`LOWER_IS_BETTER`)
Used when lower numerical values represent healthier outcomes (debt payment ratio, expense-to-income ratio).
$$\text{score} = \begin{cases} 
100.0 & \text{if } \text{value} \le \text{good\_threshold} \\
0.0 & \text{if } \text{value} \ge \text{bad\_threshold} \\
\left(1.0 - \frac{\text{value} - \text{good\_threshold}}{\text{bad\_threshold} - \text{good\_threshold}}\right) \times 100.0 & \text{otherwise}
\end{cases}$$

### 2.3 Target Range (`TARGET_RANGE`)
Used when both too little and too much are undesirable (e.g. sleep duration, caloric intake).
- Values inside $[\text{optimal\_min}, \text{optimal\_max}] = 100.0$
- Values between $\text{min\_tolerance}$ and $\text{optimal\_min}$ scale linearly $0 \rightarrow 100$
- Values between $\text{optimal\_max}$ and $\text{max\_tolerance}$ scale linearly $100 \rightarrow 0$
- Values outside tolerances $= 0.0$

### 2.4 Positive Subjective Rating (`RATING`)
Maps 1–5 Likert scales to 0–100:
$$\text{score} = \frac{\text{rating} - 1}{4} \times 100$$
- $1 \rightarrow 0.0$
- $2 \rightarrow 25.0$
- $3 \rightarrow 50.0$
- $4 \rightarrow 75.0$
- $5 \rightarrow 100.0$

### 2.5 Inverse Subjective Rating (`INVERSE_RATING`)
Maps negative subjective factors (stress, loneliness) where 1 is best and 5 is worst:
$$\text{score} = \frac{5 - \text{rating}}{4} \times 100$$
- $1 \rightarrow 100.0$ (Low stress / Low loneliness)
- $2 \rightarrow 75.0$
- $3 \rightarrow 50.0$
- $4 \rightarrow 25.0$
- $5 \rightarrow 0.0$ (Severe stress / High loneliness)

---

## 3. Domain Scoring Weights & Rules

### 3.1 Health Domain (Total Expected Weight: 100)
Evaluated from `Health Daily Record` and supplemented by `Health Activity`.

| Component | Weight | Source Fields | Normalization Rule |
| :--- | :---: | :--- | :--- |
| **Sleep** | 30% | `sleep_hours`, `sleep_quality` | Optimal: 7.0–9.0 hrs, Tolerance: 4.0–12.0 hrs; Quality: 1–5 rating |
| **Exercise** | 20% | `exercise_minutes`, `Health Activity.duration_minutes` | Target: 45 min/day (capped at 100) |
| **General Activity** | 15% | `steps`, `active_minutes` | Target: 10,000 steps and 30 active minutes |
| **Nutrition** | 15% | `fruit_veg_servings`, `protein_grams`, `calories_consumed` | Target: 5 servings fruit/veg, 60g protein, 1800–2500 cal |
| **Hydration** | 10% | `water_liters` | Target: 2.5 Liters |
| **Self-Reported** | 10% | `self_rated_health`, `energy_level` | Rating 1–5 ($1\rightarrow 0, 5\rightarrow 100$) |

---

### 3.2 Financial Domain (Total Expected Weight: 100)
Evaluated from latest `Financial Snapshot` (on or before target date) and check-in stress.

| Component | Weight | Source Fields | Normalization Rule |
| :--- | :---: | :--- | :--- |
| **Savings Behavior** | 30% | `monthly_income`, `monthly_expenses` | Savings Rate = $(I - E) / I$. Target: $\ge 20\%$ scores 100 |
| **Expense Management**| 25% | `monthly_expenses`, `monthly_income`, `budget_amount` | Expense Ratio = $E / I$. Optimal $\le 70\%$, Max $100\%$ |
| **Debt Burden** | 20% | `monthly_debt_payment`, `monthly_income`, `outstanding_debt`| Debt Payment Ratio = $D / I$. Optimal $\le 15\%$, Max $35\%$ |
| **Emergency Fund** | 15% | `emergency_fund`, `liquid_savings`, `essential_monthly_expenses` | Coverage = $\text{Liquid} / \text{Essential}$. Target: $\ge 6.0$ months |
| **Financial Stress** | 10% | `financial_stress_rating` or check-in `financial_stress` | Inverse rating 1–5 ($1\rightarrow 100, 5\rightarrow 0$) |

#### Zero / Missing Income Safety Rule
If income is missing or $\le 0$:
- We **never** divide by zero.
- We do **not** assign a punitive 0.0 score.
- Income-dependent metrics (Savings Rate, Debt Payment Ratio) are excluded.
- Weights are renormalized across available metrics (Emergency Fund, Financial Stress).

---

### 3.3 Social Domain (Total Expected Weight: 100)
Evaluated from `Social Activity` and `Subjective Wellbeing Checkin`. Prioritizes connection depth and interaction quality over raw message/call count.

| Component | Weight | Source Fields | Normalization Rule |
| :--- | :---: | :--- | :--- |
| **Interaction Quality**| 25% | `Social Activity.interaction_quality` | Average of logged activities (1–5 scale) |
| **Connection Level** | 25% | `Social Activity.connection_level`, `Subjective Wellbeing Checkin.social_connection` | Blend of activity connection and daily checkin (1–5 scale) |
| **Social Satisfaction**| 20% | `Subjective Wellbeing Checkin.social_satisfaction` | Subjective daily satisfaction (1–5 scale) |
| **Loneliness** | 15% | `Subjective Wellbeing Checkin.loneliness` | **Inverse rating** ($1 \rightarrow 100, 5 \rightarrow 0$) |
| **Mood Impact** | 15% | `Social Activity.mood_after`, `Subjective Wellbeing Checkin.mood` | Subjective mood reflection (1–5 scale) |

---

## 4. Missing Data, Weight Renormalization & Confidence

### Weight Renormalization Formula
When a metric has no data, it is excluded from the denominator. The score is calculated exclusively from available data:
$$\text{Domain Score} = \frac{\sum_{i \in \text{Available}} (\text{score}_i \times \text{weight}_i)}{\sum_{i \in \text{Available}} \text{weight}_i}$$

### Confidence vs Score
Score and confidence are strictly separated:
$$\text{Confidence} = \frac{\sum_{i \in \text{Available}} \text{weight}_i}{\text{Total Expected Weight}} \times 100.0$$

#### Concrete Example:
- User records **only** Sleep (8 hours, quality 5 $\rightarrow$ sleep score = 100.0).
- Sleep weight = 30.0. Other 70 weight points are missing.
- $\text{Health Score} = (100.0 \times 30.0) / 30.0 = \mathbf{100.0}$
- $\text{Health Confidence} = 30.0 / 100.0 \times 100.0 = \mathbf{30.0\%}$
The user is not penalized for missing metrics, but the dashboard transparently reflects that the score is based on 30% completeness.

---

## 5. Daily Overall Score

Overall score blends the 3 domains:
- **Health**: 40%
- **Financial**: 35%
- **Social**: 25%

If any category has no data (confidence = 0), it is excluded and weights are renormalized:
$$\text{Overall Score} = \frac{\sum_{c \in \text{Active}} (\text{score}_c \times \text{weight}_c)}{\sum_{c \in \text{Active}} \text{weight}_c}$$

$$\text{Overall Confidence} = (\text{conf}_H \times 0.40) + (\text{conf}_F \times 0.35) + (\text{conf}_S \times 0.25)$$

---

## 6. Historical Exponential Recency Weighting

To compute a user's current standing over 7-day, 30-day, and 90-day periods, WellPro applies continuous exponential recency decay.

### The Half-Life Model
- Default half-life: **14 days** ($t_{1/2} = 14$)
$$\lambda = \frac{\ln(2)}{t_{1/2}} = \frac{0.693147}{14} \approx 0.04951$$

For a score recorded $d$ days ago:
$$\text{recency\_weight}(d) = e^{-\lambda \cdot d}$$

Relative weights by age:
- Today ($d=0$): **100.0%** ($1.000$)
- 7 days ago ($d=7$): **70.7%** ($e^{-0.3465} \approx 0.7071$)
- 14 days ago ($d=14$): **50.0%** ($0.5000$)
- 21 days ago ($d=21$): **35.4%** ($0.3535$)
- 28 days ago ($d=28$): **25.0%** ($0.2500$)

### Incorporating Daily Confidence
An incomplete day (e.g. confidence = 20%) should not disproportionately influence historical period scores. We define the **effective weight**:
$$\text{effective\_weight}(d) = \text{recency\_weight}(d) \times \left(\frac{\text{confidence}(d)}{100.0}\right)$$

$$\text{Period Score} = \frac{\sum_d \left(\text{score}(d) \times \text{effective\_weight}(d)\right)}{\sum_d \text{effective\_weight}(d)}$$

$$\text{Period Confidence} = \frac{\sum_d \left(\text{confidence}(d) \times \text{recency\_weight}(d)\right)}{\sum_d \text{recency\_weight}(d)}$$

---

## 7. Trend Analysis

Trends compare the **recent 7-day period** (days 0–6) against the **previous 7-day period** (days 7–13):
$$\Delta = \text{recent\_7d\_score} - \text{previous\_7d\_score}$$

### Classification Thresholds
- $\Delta \ge +5.0$: `"improving"`
- $\Delta \le -5.0$: `"declining"`
- $-5.0 < \Delta < +5.0$: `"stable"`
- Fewer than 2 days of valid data in the window: `"insufficient_data"` (with `trend_change: null`)

---

## 8. Modifying Scoring Configuration Safely

All weights, targets, and decay rates are centralized in:
`well_pro/well_pro_app/services/scoring/config.py`

To adjust the algorithm (e.g. for version 2):
1. Increment `SCORING_VERSION = "v2"` in `config.py`.
2. Update weights or targets as desired.
3. Existing records remain indexed under `"v1"` in `Wellbeing Daily Score`.
4. Run `bench --site <site> execute well_pro.well_pro_app.seed.seed_development_data` or the recalculation task to populate v2 scores.
