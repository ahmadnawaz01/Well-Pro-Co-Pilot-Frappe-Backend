"""
Centralized Configuration for Wellbeing Scoring Engine (Version 1)
Supports default baseline heuristics and per-user custom scoring goals
with automatic scale conversion (e.g. 10k steps, 10k budget, 20% savings).
"""
import math
import re
from typing import Dict, Any, Optional, Tuple, Union

SCORING_VERSION = "v1"

# -------------------------------------------------------------------
# Top-Level Category Weights (Must sum to 1.0)
# -------------------------------------------------------------------
CATEGORY_WEIGHTS = {
    "health": 0.40,
    "financial": 0.35,
    "social": 0.25
}

# -------------------------------------------------------------------
# Health Scoring Weights & Heuristic Thresholds
# Note: Health thresholds are wellbeing heuristics, not medical advice.
# -------------------------------------------------------------------
HEALTH_METRIC_WEIGHTS = {
    "sleep": 30.0,
    "exercise": 20.0,
    "activity": 15.0,
    "nutrition": 15.0,
    "hydration": 10.0,
    "self_rated": 10.0
}

# Sleep parameters (hours)
SLEEP_OPTIMAL_MIN = 7.0
SLEEP_OPTIMAL_MAX = 9.0
SLEEP_TOLERANCE_MIN = 4.0
SLEEP_TOLERANCE_MAX = 12.0

# Physical activity & exercise parameters
STEPS_TARGET = 10000
ACTIVE_MINUTES_TARGET = 30
EXERCISE_MINUTES_TARGET = 45

# Nutrition & Hydration parameters
WATER_LITERS_TARGET = 2.5
FRUIT_VEG_SERVINGS_TARGET = 5.0
PROTEIN_GRAMS_TARGET = 60.0
CALORIES_OPTIMAL_MIN = 1800.0
CALORIES_OPTIMAL_MAX = 2500.0
CALORIES_TOLERANCE_MIN = 1200.0
CALORIES_TOLERANCE_MAX = 3500.0

# -------------------------------------------------------------------
# Financial Scoring Weights & Thresholds
# Note: Financial thresholds are personal wellbeing heuristics, not credit advice.
# -------------------------------------------------------------------
FINANCIAL_METRIC_WEIGHTS = {
    "savings": 30.0,
    "expense_budget": 25.0,
    "debt": 20.0,
    "emergency_fund": 15.0,
    "financial_stress": 10.0
}

TARGET_SAVINGS_RATE = 0.20           # 20% or more savings rate receives full score
OPTIMAL_DEBT_PAYMENT_RATIO = 0.15   # 15% or less monthly debt service is healthy
MAX_DEBT_PAYMENT_RATIO = 0.35       # 35% or more monthly debt service is heavily penalized
EMERGENCY_FUND_TARGET_MONTHS = 6.0  # 6 months of essential expenses
EXPENSE_RATIO_OPTIMAL = 0.70        # Expenses <= 70% of income is optimal
EXPENSE_RATIO_MAX = 1.00            # Expenses > 100% of income is penalized

# -------------------------------------------------------------------
# Social Scoring Weights & Thresholds
# -------------------------------------------------------------------
SOCIAL_METRIC_WEIGHTS = {
    "interaction_quality": 25.0,
    "connection_level": 25.0,
    "social_satisfaction": 20.0,
    "loneliness": 15.0,
    "mood_impact": 15.0
}

# -------------------------------------------------------------------
# Historical Aggregation & Recency Weights
# -------------------------------------------------------------------
DEFAULT_WINDOW = 30
SUPPORTED_WINDOWS = [7, 30, 90]
HALF_LIFE_DAYS = 14.0
DECAY_LAMBDA = math.log(2.0) / HALF_LIFE_DAYS  # ~0.0495105

# -------------------------------------------------------------------
# Trend Classification Thresholds
# -------------------------------------------------------------------
TREND_RECENT_WINDOW = 7
TREND_PREVIOUS_WINDOW = 7
TREND_IMPROVING_THRESHOLD = 5.0
TREND_DECLINING_THRESHOLD = -5.0
MIN_DATA_POINTS_FOR_TREND = 2


# -------------------------------------------------------------------
# Default Centralized Heuristic Dictionary
# -------------------------------------------------------------------
DEFAULT_SCORING_CONFIG: Dict[str, Any] = {
    # Health Heuristics
    "steps_target": STEPS_TARGET,
    "active_minutes_target": ACTIVE_MINUTES_TARGET,
    "exercise_minutes_target": EXERCISE_MINUTES_TARGET,
    "sleep_optimal_min": SLEEP_OPTIMAL_MIN,
    "sleep_optimal_max": SLEEP_OPTIMAL_MAX,
    "sleep_tolerance_min": SLEEP_TOLERANCE_MIN,
    "sleep_tolerance_max": SLEEP_TOLERANCE_MAX,
    "water_liters_target": WATER_LITERS_TARGET,
    "fruit_veg_servings_target": FRUIT_VEG_SERVINGS_TARGET,
    "protein_grams_target": PROTEIN_GRAMS_TARGET,
    "calories_optimal_min": CALORIES_OPTIMAL_MIN,
    "calories_optimal_max": CALORIES_OPTIMAL_MAX,
    "calories_tolerance_min": CALORIES_TOLERANCE_MIN,
    "calories_tolerance_max": CALORIES_TOLERANCE_MAX,

    # Financial Heuristics
    "budget_amount": None,                 # User monthly spending budget; None applies standard expense ratio
    "target_savings_rate": TARGET_SAVINGS_RATE,
    "optimal_debt_payment_ratio": OPTIMAL_DEBT_PAYMENT_RATIO,
    "max_debt_payment_ratio": MAX_DEBT_PAYMENT_RATIO,
    "emergency_fund_target_months": EMERGENCY_FUND_TARGET_MONTHS,
    "expense_ratio_optimal": EXPENSE_RATIO_OPTIMAL,
    "expense_ratio_max": EXPENSE_RATIO_MAX,
}

# Canonical Mapping for Goal Names and Aliases
GOAL_FIELD_ALIASES: Dict[str, str] = {
    # Steps
    "steps": "steps_target",
    "step": "steps_target",
    "steps_target": "steps_target",
    "step_target": "steps_target",
    "step_goal": "steps_target",
    "steps_goal": "steps_target",
    "daily_steps": "steps_target",

    # Financial Budget
    "budget": "budget_amount",
    "budget_amount": "budget_amount",
    "financial_budget": "budget_amount",
    "monthly_budget": "budget_amount",
    "expense_budget": "budget_amount",
    "spending_budget": "budget_amount",

    # Savings Rate
    "savings_rate": "target_savings_rate",
    "target_savings_rate": "target_savings_rate",
    "savings_goal": "target_savings_rate",
    "savings": "target_savings_rate",

    # Debt Ratios
    "debt_ratio": "optimal_debt_payment_ratio",
    "optimal_debt_payment_ratio": "optimal_debt_payment_ratio",
    "debt_payment_ratio": "optimal_debt_payment_ratio",
    "max_debt_ratio": "max_debt_payment_ratio",
    "max_debt_payment_ratio": "max_debt_payment_ratio",

    # Emergency Fund
    "emergency_fund": "emergency_fund_target_months",
    "emergency_fund_months": "emergency_fund_target_months",
    "emergency_fund_target_months": "emergency_fund_target_months",

    # Expense Ratios
    "expense_ratio_optimal": "expense_ratio_optimal",
    "optimal_expense_ratio": "expense_ratio_optimal",
    "expense_ratio_max": "expense_ratio_max",
    "max_expense_ratio": "expense_ratio_max",

    # Physical Activity & Exercise
    "active_minutes": "active_minutes_target",
    "active_minutes_target": "active_minutes_target",
    "daily_active_minutes": "active_minutes_target",
    "exercise_minutes": "exercise_minutes_target",
    "exercise_minutes_target": "exercise_minutes_target",
    "workout_minutes": "exercise_minutes_target",

    # Sleep
    "sleep_min": "sleep_optimal_min",
    "sleep_optimal_min": "sleep_optimal_min",
    "sleep_max": "sleep_optimal_max",
    "sleep_optimal_max": "sleep_optimal_max",
    "sleep_tolerance_min": "sleep_tolerance_min",
    "sleep_tolerance_max": "sleep_tolerance_max",

    # Hydration & Nutrition
    "water": "water_liters_target",
    "water_liters": "water_liters_target",
    "water_liters_target": "water_liters_target",
    "fruit_veg": "fruit_veg_servings_target",
    "fruit_veg_servings": "fruit_veg_servings_target",
    "fruit_veg_servings_target": "fruit_veg_servings_target",
    "protein": "protein_grams_target",
    "protein_grams": "protein_grams_target",
    "protein_grams_target": "protein_grams_target",
    "calories_min": "calories_optimal_min",
    "calories_optimal_min": "calories_optimal_min",
    "calories_max": "calories_optimal_max",
    "calories_optimal_max": "calories_optimal_max",
}


def convert_goal_to_config_scale(field: str, raw_value: Any) -> Tuple[str, Any]:
    """
    Normalizes and converts raw goal input values (e.g. '10k', '20%', '2500ml', '$10,000')
    into the exact config scale of values used by the scoring engine.
    """
    field_cleaned = str(field).strip().lower().replace("-", "_").replace(" ", "_")
    canonical_key = GOAL_FIELD_ALIASES.get(field_cleaned, field_cleaned)

    if raw_value is None or canonical_key not in DEFAULT_SCORING_CONFIG:
        return canonical_key, None

    # Handle string cleaning and parsing
    if isinstance(raw_value, str):
        cleaned = raw_value.strip().replace(",", "").replace("$", "")

        # Percentage string e.g. "20%" -> 0.20
        if cleaned.endswith("%"):
            try:
                num = float(cleaned[:-1].strip()) / 100.0
                return canonical_key, round(max(0.0, num), 4)
            except ValueError:
                pass

        # Volume in milliliters e.g. "2500ml" -> 2.5
        if cleaned.lower().endswith("ml"):
            try:
                num = float(cleaned[:-2].strip()) / 1000.0
                return canonical_key, round(max(0.0, num), 2)
            except ValueError:
                pass

        # Liters e.g. "2.5L" -> 2.5
        if cleaned.lower().endswith("l") and not cleaned.lower().endswith("cal"):
            try:
                num = float(cleaned[:-1].strip())
                return canonical_key, round(max(0.0, num), 2)
            except ValueError:
                pass

        # Grams e.g. "60g" -> 60.0
        if cleaned.lower().endswith("g") and not cleaned.lower().endswith("kg"):
            try:
                num = float(cleaned[:-1].strip())
                return canonical_key, round(max(0.0, num), 2)
            except ValueError:
                pass

        # Time with hours e.g. "1.5h" or "8 hrs"
        m_h = re.match(r"^([0-9]+(?:\.[0-9]+)?)\s*(?:h|hrs?|hours?)$", cleaned, re.IGNORECASE)
        if m_h:
            h_val = float(m_h.group(1))
            if "minutes" in canonical_key:
                return canonical_key, int(round(h_val * 60))
            return canonical_key, round(h_val, 2)

        # Time with minutes e.g. "45m" or "30 mins"
        m_m = re.match(r"^([0-9]+(?:\.[0-9]+)?)\s*(?:m|mins?|minutes?)$", cleaned, re.IGNORECASE)
        if m_m:
            m_val = float(m_m.group(1))
            if "sleep" in canonical_key:
                return canonical_key, round(m_val / 60.0, 2)
            return canonical_key, int(round(m_val))

        # Check for k, m, b suffixes e.g. "10k" -> 10000.0
        m_num = re.match(r"^([0-9]+(?:\.[0-9]+)?)\s*([kKmMbB]?)$", cleaned)
        if m_num:
            val = float(m_num.group(1))
            suf = m_num.group(2).lower()
            if suf == "k":
                val *= 1000.0
            elif suf == "m":
                val *= 1000000.0
            elif suf == "b":
                val *= 1000000000.0
            raw_value = val
        else:
            try:
                raw_value = float(cleaned)
            except ValueError:
                digits = re.sub(r"[^\d.]", "", cleaned)
                raw_value = float(digits) if digits else 0.0

    # Ensure numeric
    try:
        val = float(raw_value)
    except (ValueError, TypeError):
        return canonical_key, None

    # Scale according to target field type
    if canonical_key == "steps_target":
        return canonical_key, max(0, int(round(val)))

    if canonical_key in ("active_minutes_target", "exercise_minutes_target"):
        return canonical_key, max(0, int(round(val)))

    if canonical_key in (
        "target_savings_rate",
        "optimal_debt_payment_ratio",
        "max_debt_payment_ratio",
        "expense_ratio_optimal",
        "expense_ratio_max"
    ):
        # Ratio scale: if given as percentage > 1.0 (e.g. 20 or 25.0), scale down to 0.0-1.0
        if val > 1.0:
            val = val / 100.0
        return canonical_key, round(max(0.0, min(val, 1.0)), 4)

    if canonical_key == "budget_amount":
        return canonical_key, round(max(0.0, val), 2)

    return canonical_key, round(max(0.0, val), 2)


def parse_custom_goals(raw_goals: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parses a dictionary of raw goals and converts each key and value
    to the canonical config scale.
    """
    parsed = {}
    if not raw_goals or not isinstance(raw_goals, dict):
        return parsed

    for k, v in raw_goals.items():
        if v is None:
            continue
        canonical_key, scaled_val = convert_goal_to_config_scale(str(k), v)
        if canonical_key in DEFAULT_SCORING_CONFIG and scaled_val is not None:
            parsed[canonical_key] = scaled_val

    return parsed


def get_user_custom_goals(user: Optional[str] = None) -> Dict[str, Any]:
    """
    Safely retrieves persisted custom scoring goals for a specific user from WellPro Profile.
    Returns an empty dict if the user has no custom goals.
    """
    if not user:
        return {}

    try:
        import frappe
        if hasattr(frappe, "db") and frappe.db:
            raw = frappe.db.get_value("WellPro Profile", {"user": user}, "custom_scoring_goals")
            if raw and isinstance(raw, str):
                import json
                try:
                    data = json.loads(raw)
                    if isinstance(data, dict):
                        return {k: v for k, v in data.items() if k in DEFAULT_SCORING_CONFIG and v is not None}
                except (json.JSONDecodeError, TypeError):
                    pass
            elif isinstance(raw, dict):
                return {k: v for k, v in raw.items() if k in DEFAULT_SCORING_CONFIG and v is not None}
    except Exception:
        pass

    return {}


def get_user_scoring_config(user: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns the complete scoring configuration for a user.
    If the user has customized goals (e.g. steps = 10k, financial budget = 10k),
    those are applied. Any non-customized parameter automatically falls back
    to the default heuristics defined in this module.
    """
    cfg = dict(DEFAULT_SCORING_CONFIG)
    if user:
        user_goals = get_user_custom_goals(user)
        if user_goals:
            cfg.update(user_goals)
    return cfg
