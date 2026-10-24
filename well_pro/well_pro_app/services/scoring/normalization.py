"""
Metric Normalization Utilities
Supports HIGHER_IS_BETTER, LOWER_IS_BETTER, TARGET_RANGE, RATING, and INVERSE_RATING.
Guarantees clamp to 0.0 - 100.0, handles None/missing, avoids division by zero.
"""
from typing import Optional, Union

def clamp(value: Union[int, float], min_val: float = 0.0, max_val: float = 100.0) -> float:
    """Constrains a numeric value strictly between min_val and max_val."""
    try:
        val_f = float(value)
        return max(min_val, min(val_f, max_val))
    except (ValueError, TypeError):
        return min_val


def normalize_rating(rating: Optional[Union[int, float]], min_rating: float = 1.0, max_rating: float = 5.0) -> Optional[float]:
    """
    Normalizes a positive subjective rating (e.g. 1-5 scale) to 0-100:
    1 -> 0, 2 -> 25, 3 -> 50, 4 -> 75, 5 -> 100.
    Formula: ((rating - min_rating) / (max_rating - min_rating)) * 100
    """
    if rating is None:
        return None
    try:
        r = float(rating)
        if max_rating <= min_rating:
            return 50.0
        score = ((r - min_rating) / (max_rating - min_rating)) * 100.0
        return round(clamp(score), 4)
    except (ValueError, TypeError):
        return None


def normalize_inverse_rating(rating: Optional[Union[int, float]], min_rating: float = 1.0, max_rating: float = 5.0) -> Optional[float]:
    """
    Normalizes a negative subjective metric (e.g. stress or loneliness 1-5 scale) to 0-100:
    1 -> 100, 2 -> 75, 3 -> 50, 4 -> 25, 5 -> 0.
    Formula: ((max_rating - rating) / (max_rating - min_rating)) * 100
    """
    if rating is None:
        return None
    try:
        r = float(rating)
        if max_rating <= min_rating:
            return 50.0
        score = ((max_rating - r) / (max_rating - min_rating)) * 100.0
        return round(clamp(score), 4)
    except (ValueError, TypeError):
        return None


def normalize_higher_is_better(value: Optional[Union[int, float]], target: float, cap_multiplier: float = 1.0) -> Optional[float]:
    """
    Normalizes progress toward a positive target:
    score = min(value / target, cap_multiplier) * 100.
    Never divides by zero.
    """
    if value is None:
        return None
    try:
        val_f = float(value)
        if target <= 0.0:
            return 100.0 if val_f > 0 else 0.0
        ratio = min(val_f / target, cap_multiplier)
        return round(clamp(ratio * 100.0), 4)
    except (ValueError, TypeError):
        return None


def normalize_lower_is_better(value: Optional[Union[int, float]], good_threshold: float, bad_threshold: float) -> Optional[float]:
    """
    Normalizes metrics where lower values represent better outcomes (e.g. debt-to-income).
    <= good_threshold: 100.0
    >= bad_threshold: 0.0
    Linear decay in between.
    """
    if value is None:
        return None
    try:
        val_f = float(value)
        if bad_threshold <= good_threshold:
            return 100.0 if val_f <= good_threshold else 0.0
        if val_f <= good_threshold:
            return 100.0
        if val_f >= bad_threshold:
            return 0.0
        score = (1.0 - (val_f - good_threshold) / (bad_threshold - good_threshold)) * 100.0
        return round(clamp(score), 4)
    except (ValueError, TypeError):
        return None


def normalize_target_range(
    value: Optional[Union[int, float]],
    optimal_min: float,
    optimal_max: float,
    min_tolerance: float,
    max_tolerance: float
) -> Optional[float]:
    """
    Values inside [optimal_min, optimal_max] receive 100.
    Values between min_tolerance and optimal_min scale linearly from 0 to 100.
    Values between optimal_max and max_tolerance scale linearly from 100 to 0.
    Values outside tolerances receive 0.
    """
    if value is None:
        return None
    try:
        val_f = float(value)
        if optimal_min <= val_f <= optimal_max:
            return 100.0
        if val_f < optimal_min:
            if val_f <= min_tolerance or optimal_min <= min_tolerance:
                return 0.0
            score = ((val_f - min_tolerance) / (optimal_min - min_tolerance)) * 100.0
            return round(clamp(score), 4)
        else:
            if val_f >= max_tolerance or max_tolerance <= optimal_max:
                return 0.0
            score = ((max_tolerance - val_f) / (max_tolerance - optimal_max)) * 100.0
            return round(clamp(score), 4)
    except (ValueError, TypeError):
        return None
