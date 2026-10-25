"""
Health Wellbeing Domain Scoring Engine
Processes Sleep, Physical Activity, Exercise, Nutrition, Hydration, and Self-Reported Vitals.
Supports both default baseline heuristics and per-user custom scoring goals.
"""
from typing import Tuple, Optional, Any
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
    CALORIES_TOLERANCE_MAX,
    get_user_scoring_config
)
from well_pro.well_pro_app.services.scoring.normalization import (
    clamp,
    normalize_target_range,
    normalize_higher_is_better,
    normalize_rating
)

def accumulate_daily_health_record(user: str, target_date: str) -> Optional[str]:
    """
    Syncs individual Health Activity records for a user on a given date
    into the master Health Daily Record for that date.
    """
    if getattr(frappe.flags, "in_accumulation", False):
        return None
    activities = frappe.db.get_all(
        "Health Activity",
        filters={
            "user": user,
            "logged_at": ["between", [f"{target_date} 00:00:00", f"{target_date} 23:59:59"]]
        },
        fields=["duration_minutes", "steps", "calories_burned", "intensity"]
    )

    if not activities:
        return None

    total_activity_steps = sum(int(a.steps or 0) for a in activities)
    total_activity_mins = int(round(sum(float(a.duration_minutes or 0) for a in activities)))

    existing_name = frappe.db.exists(
        "Health Daily Record",
        {"user": user, "record_date": target_date}
    )

    if existing_name:
        doc = frappe.get_doc("Health Daily Record", existing_name)
        doc.steps = max(int(doc.steps or 0), total_activity_steps)
        doc.exercise_minutes = max(int(doc.exercise_minutes or 0), total_activity_mins)
        doc.active_minutes = max(int(doc.active_minutes or 0), total_activity_mins)
        doc.flags.ignore_hooks = True
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        return doc.name
    else:
        doc = frappe.get_doc({
            "doctype": "Health Daily Record",
            "user": user,
            "record_date": target_date,
            "steps": total_activity_steps,
            "exercise_minutes": total_activity_mins,
            "active_minutes": total_activity_mins,
            "source": "Wearable"
        })
        doc.flags.ignore_hooks = True
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return doc.name


def calculate_health_score(user: str, target_date: str) -> Tuple[float, float]:
    """
    Computes daily health score and confidence for a given user and date.
    Uses custom scoring goals if set by the user, otherwise falls back to defaults.
    Returns: (score: float, confidence: float)
    """
    # 0. Sync and accumulate any Health Activity records for this date
    try:
        accumulate_daily_health_record(user, target_date)
    except Exception as e:
        frappe.log_error(f"Health daily record accumulation failed for {user} on {target_date}: {str(e)}", "WellPro Scoring Error")

    # 1. Fetch user-specific scoring config (custom or default baseline)
    cfg = get_user_scoring_config(user)
    steps_target = cfg.get("steps_target", STEPS_TARGET)
    active_minutes_target = cfg.get("active_minutes_target", ACTIVE_MINUTES_TARGET)
    exercise_minutes_target = cfg.get("exercise_minutes_target", EXERCISE_MINUTES_TARGET)
    sleep_opt_min = cfg.get("sleep_optimal_min", SLEEP_OPTIMAL_MIN)
    sleep_opt_max = cfg.get("sleep_optimal_max", SLEEP_OPTIMAL_MAX)
    sleep_tol_min = cfg.get("sleep_tolerance_min", SLEEP_TOLERANCE_MIN)
    sleep_tol_max = cfg.get("sleep_tolerance_max", SLEEP_TOLERANCE_MAX)
    water_target = cfg.get("water_liters_target", WATER_LITERS_TARGET)
    fruit_veg_target = cfg.get("fruit_veg_servings_target", FRUIT_VEG_SERVINGS_TARGET)
    protein_target = cfg.get("protein_grams_target", PROTEIN_GRAMS_TARGET)
    cal_opt_min = cfg.get("calories_optimal_min", CALORIES_OPTIMAL_MIN)
    cal_opt_max = cfg.get("calories_optimal_max", CALORIES_OPTIMAL_MAX)
    cal_tol_min = cfg.get("calories_tolerance_min", CALORIES_TOLERANCE_MIN)
    cal_tol_max = cfg.get("calories_tolerance_max", CALORIES_TOLERANCE_MAX)

    # 2. Fetch Health Daily Record
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

    # 3. Fetch any Health Activity records logged on target date to supplement
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
            sleep_opt_min,
            sleep_opt_max,
            sleep_tol_min,
            sleep_tol_max
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
        exercise_mins = float(rec.exercise_minutes)
        has_exercise_data = True
    if activities:
        act_mins = sum(float(a.duration_minutes or 0) for a in activities)
        if act_mins > 0:
            exercise_mins = max(exercise_mins, act_mins)
            has_exercise_data = True

    if has_exercise_data:
        ex_score = normalize_higher_is_better(exercise_mins, exercise_minutes_target)
        if ex_score is not None:
            component_scores["exercise"] = ex_score
            available_weights["exercise"] = HEALTH_METRIC_WEIGHTS["exercise"]

    # Component 3: General Activity (weight = 15)
    activity_parts = []
    total_steps = 0.0
    has_steps_data = False
    if rec and rec.steps is not None:
        total_steps = float(rec.steps)
        has_steps_data = True
    if activities:
        act_steps = sum(int(a.steps or 0) for a in activities)
        if act_steps > 0:
            total_steps = max(total_steps, float(act_steps))
            has_steps_data = True

    if has_steps_data and total_steps > 0:
        steps_score = normalize_higher_is_better(total_steps, steps_target)
        if steps_score is not None:
            activity_parts.append(steps_score)

    if rec and rec.active_minutes is not None:
        active_score = normalize_higher_is_better(rec.active_minutes, active_minutes_target)
        if active_score is not None:
            activity_parts.append(active_score)

    if activity_parts:
        component_scores["activity"] = sum(activity_parts) / len(activity_parts)
        available_weights["activity"] = HEALTH_METRIC_WEIGHTS["activity"]

    # Component 4: Nutrition (weight = 15)
    nutrition_parts = []
    if rec and rec.fruit_veg_servings is not None:
        fv_score = normalize_higher_is_better(rec.fruit_veg_servings, fruit_veg_target)
        if fv_score is not None:
            nutrition_parts.append(fv_score)

    if rec and rec.protein_grams is not None:
        prot_score = normalize_higher_is_better(rec.protein_grams, protein_target)
        if prot_score is not None:
            nutrition_parts.append(prot_score)

    if rec and rec.calories_consumed is not None:
        cal_score = normalize_target_range(
            rec.calories_consumed,
            cal_opt_min,
            cal_opt_max,
            cal_tol_min,
            cal_tol_max
        )
        if cal_score is not None:
            nutrition_parts.append(cal_score)

    if nutrition_parts:
        component_scores["nutrition"] = sum(nutrition_parts) / len(nutrition_parts)
        available_weights["nutrition"] = HEALTH_METRIC_WEIGHTS["nutrition"]

    # Component 5: Hydration (weight = 10)
    if rec and rec.water_liters is not None:
        water_score = normalize_higher_is_better(rec.water_liters, water_target)
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
