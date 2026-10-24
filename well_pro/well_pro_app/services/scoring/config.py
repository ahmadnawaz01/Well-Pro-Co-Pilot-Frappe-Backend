"""
Centralized Configuration for Wellbeing Scoring Engine (Version 1)
"""
import math

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
