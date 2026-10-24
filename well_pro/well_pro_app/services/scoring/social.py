"""
Social Wellbeing Domain Scoring Engine
Processes Interaction Quality, Connection Level, Social Satisfaction, Loneliness (inverted), and Mood Impact.
Prioritizes depth and connection quality over raw interaction volume.
"""
from typing import Tuple
import frappe
from well_pro.well_pro_app.services.scoring.config import SOCIAL_METRIC_WEIGHTS
from well_pro.well_pro_app.services.scoring.normalization import (
    clamp,
    normalize_rating,
    normalize_inverse_rating
)

def calculate_social_score(user: str, target_date: str) -> Tuple[float, float]:
    """
    Computes daily social score and confidence for a given user and date.
    Returns: (score: float, confidence: float)
    """
    # 1. Fetch Social Activity records logged on target date
    activities = frappe.db.get_all(
        "Social Activity",
        filters={
            "user": user,
            "logged_at": ["between", [f"{target_date} 00:00:00", f"{target_date} 23:59:59"]]
        },
        fields=["interaction_quality", "connection_level", "mood_after"]
    )

    # 2. Fetch Subjective Wellbeing Checkin for target date
    checkin = frappe.db.get_value(
        "Subjective Wellbeing Checkin",
        {"user": user, "date": target_date},
        ["mood", "social_connection", "loneliness", "social_satisfaction"],
        as_dict=True
    )

    if not activities and not checkin:
        return 0.0, 0.0

    component_scores = {}
    available_weights = {}
    total_expected_weight = sum(SOCIAL_METRIC_WEIGHTS.values())

    # Component 1: Interaction Quality (weight = 25)
    if activities:
        valid_qualities = [a.interaction_quality for a in activities if a.interaction_quality is not None]
        if valid_qualities:
            avg_q = sum(valid_qualities) / len(valid_qualities)
            q_score = normalize_rating(avg_q)
            if q_score is not None:
                component_scores["interaction_quality"] = q_score
                available_weights["interaction_quality"] = SOCIAL_METRIC_WEIGHTS["interaction_quality"]

    # Component 2: Connection Level (weight = 25)
    connection_parts = []
    if activities:
        valid_conn = [a.connection_level for a in activities if a.connection_level is not None]
        if valid_conn:
            connection_parts.append(sum(valid_conn) / len(valid_conn))
    if checkin and checkin.social_connection is not None:
        connection_parts.append(float(checkin.social_connection))

    if connection_parts:
        avg_conn = sum(connection_parts) / len(connection_parts)
        conn_score = normalize_rating(avg_conn)
        if conn_score is not None:
            component_scores["connection_level"] = conn_score
            available_weights["connection_level"] = SOCIAL_METRIC_WEIGHTS["connection_level"]

    # Component 3: Social Satisfaction (weight = 20)
    if checkin and checkin.social_satisfaction is not None:
        sat_score = normalize_rating(checkin.social_satisfaction)
        if sat_score is not None:
            component_scores["social_satisfaction"] = sat_score
            available_weights["social_satisfaction"] = SOCIAL_METRIC_WEIGHTS["social_satisfaction"]

    # Component 4: Loneliness (weight = 15, Inverse Rating)
    # 1 = Low loneliness (Best, 100), 5 = High loneliness (Worst, 0)
    if checkin and checkin.loneliness is not None:
        lone_score = normalize_inverse_rating(checkin.loneliness)
        if lone_score is not None:
            component_scores["loneliness"] = lone_score
            available_weights["loneliness"] = SOCIAL_METRIC_WEIGHTS["loneliness"]

    # Component 5: Mood / Subjective Impact (weight = 15)
    mood_parts = []
    if activities:
        valid_mood = [a.mood_after for a in activities if a.mood_after is not None]
        if valid_mood:
            mood_parts.append(sum(valid_mood) / len(valid_mood))
    if checkin and checkin.mood is not None:
        mood_parts.append(float(checkin.mood))

    if mood_parts:
        avg_mood = sum(mood_parts) / len(mood_parts)
        mood_score = normalize_rating(avg_mood)
        if mood_score is not None:
            component_scores["mood_impact"] = mood_score
            available_weights["mood_impact"] = SOCIAL_METRIC_WEIGHTS["mood_impact"]

    # Renormalize weights among available metrics
    sum_avail = sum(available_weights.values())
    if sum_avail == 0:
        return 0.0, 0.0

    final_score = sum(component_scores[k] * available_weights[k] for k in component_scores) / sum_avail
    confidence = (sum_avail / total_expected_weight) * 100.0

    return round(clamp(final_score), 1), round(clamp(confidence), 1)
