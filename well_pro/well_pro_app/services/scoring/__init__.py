"""
WellPro Wellbeing Scoring Package
"""
from well_pro.well_pro_app.services.scoring.config import (
    SCORING_VERSION,
    DEFAULT_SCORING_CONFIG,
    convert_goal_to_config_scale,
    parse_custom_goals,
    get_user_custom_goals,
    get_user_scoring_config
)
from well_pro.well_pro_app.services.scoring.normalization import clamp
from well_pro.well_pro_app.services.scoring.health import (
    calculate_health_score,
    accumulate_daily_health_record
)
from well_pro.well_pro_app.services.scoring.financial import (
    calculate_financial_score,
    accumulate_daily_financial_snapshot
)
from well_pro.well_pro_app.services.scoring.social import calculate_social_score
from well_pro.well_pro_app.services.scoring.aggregation import (
    calculate_overall_score,
    calculate_recency_weighted_score,
    calculate_trend
)
from well_pro.well_pro_app.services.scoring.service import (
    calculate_daily_score,
    get_user_dashboard
)

__all__ = [
    "SCORING_VERSION",
    "DEFAULT_SCORING_CONFIG",
    "convert_goal_to_config_scale",
    "parse_custom_goals",
    "get_user_custom_goals",
    "get_user_scoring_config",
    "clamp",
    "calculate_health_score",
    "accumulate_daily_health_record",
    "calculate_financial_score",
    "accumulate_daily_financial_snapshot",
    "calculate_social_score",
    "calculate_overall_score",
    "calculate_recency_weighted_score",
    "calculate_trend",
    "calculate_daily_score",
    "get_user_dashboard",
]
