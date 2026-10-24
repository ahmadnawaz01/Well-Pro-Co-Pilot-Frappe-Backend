"""
Financial Domain Scoring Engine
Evaluates Savings Rate, Expense Management, Debt Burden, Emergency Fund, and Financial Stress.
Handles missing income, zero expenses, and renormalizes available weights safely.
"""
from typing import Tuple
import frappe
from well_pro.well_pro_app.services.scoring.config import (
    FINANCIAL_METRIC_WEIGHTS,
    TARGET_SAVINGS_RATE,
    OPTIMAL_DEBT_PAYMENT_RATIO,
    MAX_DEBT_PAYMENT_RATIO,
    EMERGENCY_FUND_TARGET_MONTHS,
    EXPENSE_RATIO_OPTIMAL,
    EXPENSE_RATIO_MAX
)
from well_pro.well_pro_app.services.scoring.normalization import (
    clamp,
    normalize_rating,
    normalize_inverse_rating,
    normalize_higher_is_better,
    normalize_lower_is_better
)

def calculate_financial_score(user: str, target_date: str) -> Tuple[float, float]:
    """
    Computes daily financial score and confidence for a given user and date.
    Returns: (score: float, confidence: float)
    """
    # 1. Fetch latest Financial Snapshot on or before target date
    snap = frappe.db.get_value(
        "Financial Snapshot",
        {"user": user, "snapshot_date": ["<=", target_date]},
        [
            "monthly_income", "monthly_expenses", "essential_monthly_expenses",
            "liquid_savings", "investment_value", "emergency_fund",
            "budget_amount", "outstanding_debt", "monthly_debt_payment",
            "financial_stress_rating"
        ],
        order_by="snapshot_date desc",
        as_dict=True
    )

    # 2. Check for check-in financial stress rating if snapshot missing it
    checkin_stress = frappe.db.get_value(
        "Subjective Wellbeing Checkin",
        {"user": user, "date": target_date},
        "financial_stress"
    )

    if not snap and checkin_stress is None:
        return 0.0, 0.0

    component_scores = {}
    available_weights = {}
    total_expected_weight = sum(FINANCIAL_METRIC_WEIGHTS.values())

    income = float(snap.monthly_income or 0.0) if snap else 0.0
    expenses = float(snap.monthly_expenses or 0.0) if snap else 0.0
    has_income = income > 0.0

    # Component 1: Savings Behavior (weight = 30)
    # Savings Rate = (income - expenses) / income
    if has_income:
        savings_amount = max(0.0, income - expenses)
        savings_rate = savings_amount / income
        # Target: >= 20% savings rate scores 100
        sav_score = normalize_higher_is_better(savings_rate, TARGET_SAVINGS_RATE)
        if sav_score is not None:
            component_scores["savings"] = sav_score
            available_weights["savings"] = FINANCIAL_METRIC_WEIGHTS["savings"]

    # Component 2: Expense / Budget Management (weight = 25)
    if has_income:
        expense_ratio = expenses / income
        # Expenses <= 70% of income is optimal (100), >= 100% of income is penalized (0)
        exp_score = normalize_lower_is_better(expense_ratio, EXPENSE_RATIO_OPTIMAL, EXPENSE_RATIO_MAX)
        if exp_score is not None:
            component_scores["expense_budget"] = exp_score
            available_weights["expense_budget"] = FINANCIAL_METRIC_WEIGHTS["expense_budget"]
    elif snap and snap.budget_amount and float(snap.budget_amount) > 0 and expenses > 0:
        # If income missing but budget set, compare expenses to budget
        budget_ratio = expenses / float(snap.budget_amount)
        bud_score = normalize_lower_is_better(budget_ratio, 1.0, 1.3)
        if bud_score is not None:
            component_scores["expense_budget"] = bud_score
            available_weights["expense_budget"] = FINANCIAL_METRIC_WEIGHTS["expense_budget"]

    # Component 3: Debt Burden (weight = 20)
    # Debt Payment Ratio = monthly_debt_payment / monthly_income
    if has_income and snap and snap.monthly_debt_payment is not None:
        debt_payment = float(snap.monthly_debt_payment)
        dti = debt_payment / income
        dti_score = normalize_lower_is_better(dti, OPTIMAL_DEBT_PAYMENT_RATIO, MAX_DEBT_PAYMENT_RATIO)
        if dti_score is not None:
            component_scores["debt"] = dti_score
            available_weights["debt"] = FINANCIAL_METRIC_WEIGHTS["debt"]
    elif snap and snap.outstanding_debt is not None and float(snap.outstanding_debt) == 0.0:
        # Confirmed zero debt
        component_scores["debt"] = 100.0
        available_weights["debt"] = FINANCIAL_METRIC_WEIGHTS["debt"]

    # Component 4: Emergency Fund / Liquid Reserve (weight = 15)
    # Emergency Fund Coverage = emergency_fund / essential_monthly_expenses
    if snap:
        liquid = float(snap.emergency_fund or snap.liquid_savings or 0.0)
        essential = float(snap.essential_monthly_expenses or (expenses * 0.7) or 1.0)
        if essential > 0:
            coverage_months = liquid / essential
            ef_score = normalize_higher_is_better(coverage_months, EMERGENCY_FUND_TARGET_MONTHS)
            if ef_score is not None:
                component_scores["emergency_fund"] = ef_score
                available_weights["emergency_fund"] = FINANCIAL_METRIC_WEIGHTS["emergency_fund"]

    # Component 5: Financial Stress (weight = 10)
    # Inverse rating: 1 = Low stress (Best, 100), 5 = High stress (Worst, 0)
    stress_val = None
    if snap and snap.financial_stress_rating is not None:
        stress_val = snap.financial_stress_rating
    elif checkin_stress is not None:
        stress_val = checkin_stress

    if stress_val is not None:
        stress_score = normalize_inverse_rating(stress_val)
        if stress_score is not None:
            component_scores["financial_stress"] = stress_score
            available_weights["financial_stress"] = FINANCIAL_METRIC_WEIGHTS["financial_stress"]

    # Renormalize weights among available metrics
    sum_avail = sum(available_weights.values())
    if sum_avail == 0:
        return 0.0, 0.0

    final_score = sum(component_scores[k] * available_weights[k] for k in component_scores) / sum_avail
    confidence = (sum_avail / total_expected_weight) * 100.0

    return round(clamp(final_score), 1), round(clamp(confidence), 1)
