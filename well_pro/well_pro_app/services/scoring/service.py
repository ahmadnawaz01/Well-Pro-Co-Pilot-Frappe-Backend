"""
Wellbeing Scoring Service
High-level service for calculating, persisting, and retrieving daily scores and dashboard metrics.
"""
from datetime import date, datetime
from typing import Dict, Any, Optional
import frappe
from frappe.utils import today, add_days, now

from well_pro.well_pro_app.services.scoring.config import (
    SCORING_VERSION,
    SUPPORTED_WINDOWS
)
from well_pro.well_pro_app.services.scoring.health import calculate_health_score
from well_pro.well_pro_app.services.scoring.financial import calculate_financial_score
from well_pro.well_pro_app.services.scoring.social import calculate_social_score
from well_pro.well_pro_app.services.scoring.aggregation import (
    calculate_overall_score,
    calculate_recency_weighted_score,
    calculate_trend
)

def calculate_daily_score(user: str, score_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Computes Health, Financial, Social, and Overall Wellbeing scores for a user on a given date.
    Upserts the record in Wellbeing Daily Score idempotently based on (user, score_date, scoring_version).
    """
    if getattr(frappe.flags, "in_scoring", False):
        return {}

    if not score_date:
        score_date = today()

    frappe.flags.in_scoring = True
    try:
        return _calculate_daily_score_internal(user, score_date)
    finally:
        frappe.flags.in_scoring = False


def _calculate_daily_score_internal(user: str, score_date: str) -> Dict[str, Any]:

    # 1. Compute Category Scores & Confidences
    h_score, h_conf = calculate_health_score(user, score_date)
    f_score, f_conf = calculate_financial_score(user, score_date)
    s_score, s_conf = calculate_social_score(user, score_date)

    # 2. Compute Overall Score & Confidence
    o_score, o_conf = calculate_overall_score(
        h_score if h_conf > 0 else None,
        h_conf,
        f_score if f_conf > 0 else None,
        f_conf,
        s_score if s_conf > 0 else None,
        s_conf
    )

    # 3. Idempotent Upsert in Wellbeing Daily Score
    # Search by (user, score_date) only to avoid version mismatch creating duplicate records.
    # If a record exists for this user+date, always update it with fresh scores.
    existing = frappe.db.exists(
        "Wellbeing Daily Score",
        {
            "user": user,
            "score_date": score_date
        }
    )

    if existing:
        doc = frappe.get_doc("Wellbeing Daily Score", existing)
        doc.health_score = h_score
        doc.health_confidence = h_conf
        doc.financial_score = f_score
        doc.financial_confidence = f_conf
        doc.social_score = s_score
        doc.social_confidence = s_conf
        doc.overall_score = o_score or 0.0
        doc.scoring_version = SCORING_VERSION
        doc.calculated_at = now()
        doc.save(ignore_permissions=True)
    else:
        # Build a human-readable document name: SCORE-<user_short>-<date>
        user_short = user.split("@")[0][:12].upper().replace(".", "-")
        doc_name = f"SCORE-{user_short}-{score_date}"
        doc = frappe.get_doc({
            "doctype": "Wellbeing Daily Score",
            "name": doc_name,
            "user": user,
            "score_date": score_date,
            "health_score": h_score,
            "health_confidence": h_conf,
            "financial_score": f_score,
            "financial_confidence": f_conf,
            "social_score": s_score,
            "social_confidence": s_conf,
            "overall_score": o_score or 0.0,
            "scoring_version": SCORING_VERSION,
            "calculated_at": now()
        }).insert(ignore_permissions=True)

    frappe.db.commit()

    return {
        "name": doc.name,
        "user": user,
        "score_date": str(score_date),
        "health_score": h_score,
        "health_confidence": h_conf,
        "financial_score": f_score,
        "financial_confidence": f_conf,
        "social_score": s_score,
        "social_confidence": s_conf,
        "overall_score": o_score,
        "scoring_version": SCORING_VERSION,
        "calculated_at": str(doc.calculated_at)
    }


def get_user_dashboard(user: str, as_of_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Generates full multi-dimensional dashboard response with current scores,
    7-day, 30-day, 90-day exponential recency-weighted scores, and trend analysis.
    """
    if not as_of_date:
        as_of_date = today()

    target_d = datetime.strptime(str(as_of_date), "%Y-%m-%d").date()
    start_date = add_days(as_of_date, -90)

    # Refresh today's score
    today_res = calculate_daily_score(user, as_of_date)

    # Fetch last 90 days of scores for this user
    daily_records = frappe.get_all(
        "Wellbeing Daily Score",
        filters={
            "user": user,
            "score_date": [">=", start_date],
            "scoring_version": SCORING_VERSION
        },
        fields=[
            "score_date",
            "health_score", "health_confidence",
            "financial_score", "financial_confidence",
            "social_score", "social_confidence",
            "overall_score"
        ],
        order_by="score_date asc"
    )

    # Compute period metrics for each domain
    def build_domain_metrics(score_field: str, conf_field: str, today_val: Optional[float], today_conf: float):
        w7, c7 = calculate_recency_weighted_score(daily_records, score_field, conf_field, days=7, as_of_date=target_d)
        w30, c30 = calculate_recency_weighted_score(daily_records, score_field, conf_field, days=30, as_of_date=target_d)
        w90, c90 = calculate_recency_weighted_score(daily_records, score_field, conf_field, days=90, as_of_date=target_d)
        trend_info = calculate_trend(daily_records, score_field, conf_field, as_of_date=target_d)

        return {
            "today_score": today_val if today_conf > 0 else None,
            "current_score": w30 if w30 is not None else today_val,
            "confidence": round(c30, 1) if c30 is not None else today_conf,
            "seven_day_score": w7,
            "thirty_day_score": w30,
            "ninety_day_score": w90,
            "trend": trend_info["trend"],
            "trend_change": trend_info["trend_change"]
        }

    health_metrics = build_domain_metrics(
        "health_score", "health_confidence", today_res["health_score"], today_res["health_confidence"]
    )
    financial_metrics = build_domain_metrics(
        "financial_score", "financial_confidence", today_res["financial_score"], today_res["financial_confidence"]
    )
    social_metrics = build_domain_metrics(
        "social_score", "social_confidence", today_res["social_score"], today_res["social_confidence"]
    )

    # Overall Metrics
    w7_o, _ = calculate_recency_weighted_score(daily_records, "overall_score", "health_confidence", days=7, as_of_date=target_d)
    w30_o, _ = calculate_recency_weighted_score(daily_records, "overall_score", "health_confidence", days=30, as_of_date=target_d)
    w90_o, _ = calculate_recency_weighted_score(daily_records, "overall_score", "health_confidence", days=90, as_of_date=target_d)
    overall_trend = calculate_trend(daily_records, "overall_score", "health_confidence", as_of_date=target_d)

    overall_metrics = {
        "score": w30_o if w30_o is not None else today_res["overall_score"],
        "today_score": today_res["overall_score"],
        "seven_day_score": w7_o,
        "thirty_day_score": w30_o,
        "ninety_day_score": w90_o,
        "trend": overall_trend["trend"],
        "trend_change": overall_trend["trend_change"]
    }

    return {
        "health": health_metrics,
        "financial": financial_metrics,
        "social": social_metrics,
        "overall": overall_metrics,
        "scoring_version": SCORING_VERSION,
        "as_of_date": str(as_of_date)
    }
