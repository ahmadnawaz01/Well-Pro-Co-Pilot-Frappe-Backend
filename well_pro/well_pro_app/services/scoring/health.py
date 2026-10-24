"""
Health Domain Scoring Engine
Processes Sleep, Physical Activity, Exercise, Nutrition, Hydration, and Self-Reported Wellbeing.
Calculates score (0-100) and confidence/completeness (0-100) with weight renormalization.
"""
from typing import Tuple, Optional
import frappe
from well_pro.well_pro_app.services.scoring.config import (
    HEALTH_METRIC_WEIGHTS,
    SLEEP_OPTIMAL_MIN,
    SLEEP_OPTIMAL_MAX,
    SLEEP_TOLERANCE_MIN,
    SLEEP_TOLERANCE_MAX,
    STEPS_TARGET,
    ACTIVE_MINUTES_TARGET,
    EXERCISE_MINUTES_TARGET,
    WATER_LITERS_TARGET,
    FRUIT_VEG_SERVINGS_TARGET,
    PROTEIN_GRAMS_TARGET,
    CALORIES_OPTIMAL_MIN,
    CALORIES_OPTIMAL_MAX,
    CALORIES_TOLERANCE_MIN,
    CALORIES_TOLERANCE_MAX
)
from well_pro.well_pro_app.services.scoring.normalization import (
    clamp,
    normalize_rating,
    normalize_higher_is_better,
    normalize_target_range
)

def calculate_health_score(user: str, target_date: str) -> Tuple[float, float]:
    """
    Computes daily health score and confidence for a given user and date.
    Returns: (score: float, confidence: float)
    """
    # 1. Fetch Health Daily Record
    rec = frappe.db.get_value(
        "Health Daily Record",
        {"user": user, "record_date": target_date},
        [
            "sleep_hours", "sleep_quality", "steps", "active_minutes",
            "exercise_minutes", "water_liters", "calories_consumed",
            "protein_grams", "fruit_veg_servings", "energy_level",
            "self_rated_health"
        ],
        as_dict=True
    )

    # 2. Fetch any Health Activity records logged on target date to supplement
    activities = frappe.db.get_all(
        "Health Activity",
        filters={
            "user": user,
            "logged_at": ["between", [f"{target_date} 00:00:00", f"{target_date} 23:59:59"]]
        },
        fields=["duration_minutes", "steps", "calories_burned", "intensity"]
    )

    if not rec and not activities:
        return 0.0, 0.0

    component_scores = {}
    available_weights = {}
    total_expected_weight = sum(HEALTH_METRIC_WEIGHTS.values())

    # Component 1: Sleep (weight = 30)
    sleep_score_parts = []
    if rec and rec.sleep_hours is not None:
        duration_score = normalize_target_range(
            rec.sleep_hours,
            SLEEP_OPTIMAL_MIN,
            SLEEP_OPTIMAL_MAX,
            SLEEP_TOLERANCE_MIN,
            SLEEP_TOLERANCE_MAX
        )
        if duration_score is not None:
            sleep_score_parts.append(duration_score)

    if rec and rec.sleep_quality is not None:
        quality_score = normalize_rating(rec.sleep_quality)
        if quality_score is not None:
            sleep_score_parts.append(quality_score)

    if sleep_score_parts:
        component_scores["sleep"] = sum(sleep_score_parts) / len(sleep_score_parts)
        available_weights["sleep"] = HEALTH_METRIC_WEIGHTS["sleep"]

    # Component 2: Exercise (weight = 20)
    exercise_mins = 0.0
    has_exercise_data = False
    if rec and rec.exercise_minutes is not None:
        exercise_mins += float(rec.exercise_minutes)
        has_exercise_data = True
    if activities:
        act_mins = sum(float(a.duration_minutes or 0) for a in activities)
        if act_mins > 0:
            exercise_mins = max(exercise_mins, act_mins)
            has_exercise_data = True

    if has_exercise_data:
        ex_score = normalize_higher_is_better(exercise_mins, EXERCISE_MINUTES_TARGET)
        if ex_score is not None:
            component_scores["exercise"] = ex_score
            available_weights["exercise"] = HEALTH_METRIC_WEIGHTS["exercise"]

    # Component 3: General Activity (weight = 15)
    activity_parts = []
    total_steps = None
    if rec and rec.steps is not None:
        total_steps = float(rec.steps)
    elif activities:
        act_steps = sum(int(a.steps or 0) for a in activities)
        if act_steps > 0:
            total_steps = float(act_steps)

    if total_steps is not None:
        steps_score = normalize_higher_is_better(total_steps, STEPS_TARGET)
        if steps_score is not None:
            activity_parts.append(steps_score)

    if rec and rec.active_minutes is not None:
        active_score = normalize_higher_is_better(rec.active_minutes, ACTIVE_MINUTES_TARGET)
        if active_score is not None:
            activity_parts.append(active_score)

    if activity_parts:
        component_scores["activity"] = sum(activity_parts) / len(activity_parts)
        available_weights["activity"] = HEALTH_METRIC_WEIGHTS["activity"]

    # Component 4: Nutrition (weight = 15)
    nutrition_parts = []
    if rec and rec.fruit_veg_servings is not None:
        fv_score = normalize_higher_is_better(rec.fruit_veg_servings, FRUIT_VEG_SERVINGS_TARGET)
        if fv_score is not None:
            nutrition_parts.append(fv_score)

    if rec and rec.protein_grams is not None:
        prot_score = normalize_higher_is_better(rec.protein_grams, PROTEIN_GRAMS_TARGET)
        if prot_score is not None:
            nutrition_parts.append(prot_score)

    if rec and rec.calories_consumed is not None:
        cal_score = normalize_target_range(
            rec.calories_consumed,
            CALORIES_OPTIMAL_MIN,
            CALORIES_OPTIMAL_MAX,
            CALORIES_TOLERANCE_MIN,
            CALORIES_TOLERANCE_MAX
        )
        if cal_score is not None:
            nutrition_parts.append(cal_score)

    if nutrition_parts:
        component_scores["nutrition"] = sum(nutrition_parts) / len(nutrition_parts)
        available_weights["nutrition"] = HEALTH_METRIC_WEIGHTS["nutrition"]

    # Component 5: Hydration (weight = 10)
    if rec and rec.water_liters is not None:
        water_score = normalize_higher_is_better(rec.water_liters, WATER_LITERS_TARGET)
        if water_score is not None:
            component_scores["hydration"] = water_score
            available_weights["hydration"] = HEALTH_METRIC_WEIGHTS["hydration"]

    # Component 6: Self-Reported Wellbeing & Energy (weight = 10)
    self_rated_parts = []
    if rec and rec.self_rated_health is not None:
        srh_score = normalize_rating(rec.self_rated_health)
        if srh_score is not None:
            self_rated_parts.append(srh_score)

    if rec and rec.energy_level is not None:
        nrg_score = normalize_rating(rec.energy_level)
        if nrg_score is not None:
            self_rated_parts.append(nrg_score)

    if self_rated_parts:
        component_scores["self_rated"] = sum(self_rated_parts) / len(self_rated_parts)
        available_weights["self_rated"] = HEALTH_METRIC_WEIGHTS["self_rated"]

    # Renormalize weights across available components
    sum_avail = sum(available_weights.values())
    if sum_avail == 0:
        return 0.0, 0.0

    final_score = sum(component_scores[k] * available_weights[k] for k in component_scores) / sum_avail
    confidence = (sum_avail / total_expected_weight) * 100.0

    return round(clamp(final_score), 1), round(clamp(confidence), 1)
