"""
Aggregation & Trend Engine
Calculates Overall Category Scores, Exponential Recency-Weighted Period Scores, and Trends.
Implements:
  lambda = ln(2) / half_life
  weight(d) = exp(-lambda * d)
  effective_weight = recency_weight * (confidence / 100.0)
  period_score = sum(score * effective_weight) / sum(effective_weight)
"""
import math
from datetime import date, datetime
from typing import List, Dict, Tuple, Optional, Any
from well_pro.well_pro_app.services.scoring.config import (
    CATEGORY_WEIGHTS,
    HALF_LIFE_DAYS,
    TREND_RECENT_WINDOW,
    TREND_PREVIOUS_WINDOW,
    TREND_IMPROVING_THRESHOLD,
    TREND_DECLINING_THRESHOLD,
    MIN_DATA_POINTS_FOR_TREND
)
from well_pro.well_pro_app.services.scoring.normalization import clamp

def calculate_overall_score(
    health_score: Optional[float],
    health_conf: float,
    financial_score: Optional[float],
    financial_conf: float,
    social_score: Optional[float],
    social_conf: float
) -> Tuple[Optional[float], float]:
    """
    Computes overall score by renormalizing across available categories with confidence > 0.
    Returns: (overall_score: Optional[float], overall_confidence: float)
    """
    cat_scores = {
        "health": health_score,
        "financial": financial_score,
        "social": social_score
    }
    cat_confs = {
        "health": health_conf,
        "financial": financial_conf,
        "social": social_conf
    }

    avail_weights = {}
    weighted_scores = 0.0

    for cat, weight in CATEGORY_WEIGHTS.items():
        score = cat_scores.get(cat)
        conf = cat_confs.get(cat, 0.0)
        if score is not None and conf > 0.0:
            avail_weights[cat] = weight
            weighted_scores += score * weight

    # Overall confidence is the weighted blend of category confidences
    overall_confidence = (
        health_conf * CATEGORY_WEIGHTS["health"] +
        financial_conf * CATEGORY_WEIGHTS["financial"] +
        social_conf * CATEGORY_WEIGHTS["social"]
    )

    if not avail_weights:
        return None, round(clamp(overall_confidence), 1)

    overall_score = weighted_scores / sum(avail_weights.values())
    return round(clamp(overall_score), 1), round(clamp(overall_confidence), 1)


def calculate_recency_weighted_score(
    daily_records: List[Dict[str, Any]],
    score_key: str,
    conf_key: str,
    days: int = 30,
    half_life: float = HALF_LIFE_DAYS,
    as_of_date: Optional[date] = None
) -> Tuple[Optional[float], Optional[float]]:
    """
    Calculates exponential recency-weighted period score and confidence over a given window.
    effective_weight = exp(-lambda * d) * (confidence / 100.0)
    Returns: (period_score: Optional[float], period_confidence: Optional[float])
    """
    if as_of_date is None:
        as_of_date = date.today()

    decay_lambda = math.log(2.0) / half_life

    total_weighted_score = 0.0
    total_effective_weight = 0.0
    total_recency_weight = 0.0
    total_weighted_conf = 0.0

    for rec in daily_records:
        rec_date = rec.get("score_date")
        if isinstance(rec_date, str):
            rec_date = datetime.strptime(rec_date, "%Y-%m-%d").date()

        days_ago = (as_of_date - rec_date).days
        if 0 <= days_ago <= days:
            score = rec.get(score_key)
            conf = rec.get(conf_key, 0.0) or 0.0

            if score is not None and conf > 0.0:
                recency_weight = math.exp(-decay_lambda * days_ago)
                effective_weight = recency_weight * (conf / 100.0)

                total_weighted_score += float(score) * effective_weight
                total_effective_weight += effective_weight

                total_weighted_conf += float(conf) * recency_weight
                total_recency_weight += recency_weight

    if total_effective_weight == 0.0:
        return None, None

    period_score = total_weighted_score / total_effective_weight
    period_confidence = total_weighted_conf / total_recency_weight if total_recency_weight > 0 else 0.0

    return round(clamp(period_score), 1), round(clamp(period_confidence), 1)


def calculate_trend(
    daily_records: List[Dict[str, Any]],
    score_key: str,
    conf_key: str,
    as_of_date: Optional[date] = None
) -> Dict[str, Any]:
    """
    Calculates trend by comparing recent 7-day score vs previous 7-day score (days 8-14).
    Returns:
      {
        "trend": "improving" | "declining" | "stable" | "insufficient_data",
        "trend_change": float or None
      }
    """
    if as_of_date is None:
        as_of_date = date.today()

    recent_score, _ = calculate_recency_weighted_score(
        daily_records, score_key, conf_key, days=TREND_RECENT_WINDOW, as_of_date=as_of_date
    )

    # Previous 7-day period: as_of_date - 7 days
    prev_ref_date = date.fromordinal(as_of_date.toordinal() - TREND_RECENT_WINDOW)
    prev_score, _ = calculate_recency_weighted_score(
        daily_records, score_key, conf_key, days=TREND_PREVIOUS_WINDOW, as_of_date=prev_ref_date
    )

    # Count distinct records present in recent and previous windows
    recent_count = sum(
        1 for r in daily_records
        if 0 <= (as_of_date - (datetime.strptime(r["score_date"], "%Y-%m-%d").date() if isinstance(r["score_date"], str) else r["score_date"])).days <= TREND_RECENT_WINDOW
        and r.get(score_key) is not None and (r.get(conf_key) or 0) > 0
    )
    prev_count = sum(
        1 for r in daily_records
        if 1 <= (prev_ref_date - (datetime.strptime(r["score_date"], "%Y-%m-%d").date() if isinstance(r["score_date"], str) else r["score_date"])).days <= TREND_PREVIOUS_WINDOW
        and r.get(score_key) is not None and (r.get(conf_key) or 0) > 0
    )

    if recent_score is None or prev_score is None or recent_count < MIN_DATA_POINTS_FOR_TREND:
        return {
            "trend": "insufficient_data",
            "trend_change": None
        }

    trend_change = round(recent_score - prev_score, 1)

    if trend_change >= TREND_IMPROVING_THRESHOLD:
        trend_label = "improving"
    elif trend_change <= TREND_DECLINING_THRESHOLD:
        trend_label = "declining"
    else:
        trend_label = "stable"

    return {
        "trend": trend_label,
        "trend_change": trend_change
    }
