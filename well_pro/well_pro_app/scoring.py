"""
WellPro Scoring Module (Backward-Compatibility Layer)
Delegates all core scoring, normalization, and aggregation to the modular
well_pro.well_pro_app.services.scoring engine.
"""

from well_pro.well_pro_app.services.scoring import (
    SCORING_VERSION,
    clamp,
    calculate_health_score,
    calculate_financial_score,
    calculate_social_score,
    calculate_overall_score,
    calculate_recency_weighted_score,
    calculate_trend,
    calculate_daily_score,
    get_user_dashboard
)

# Backward-compatibility alias
generate_daily_wellbeing_score = calculate_daily_score

__all__ = [
    "SCORING_VERSION",
    "clamp",
    "calculate_health_score",
    "calculate_financial_score",
    "calculate_social_score",
    "calculate_overall_score",
    "calculate_recency_weighted_score",
    "calculate_trend",
    "calculate_daily_score",
    "generate_daily_wellbeing_score",
    "get_user_dashboard"
]
