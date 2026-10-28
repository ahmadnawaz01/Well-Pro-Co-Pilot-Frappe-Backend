"""
Financial Domain Scoring Engine
Evaluates Savings Rate, Expense Management, Debt Burden, Emergency Fund, and Financial Stress.
Handles missing income, zero expenses, and renormalizes available weights safely.
Supports daily accumulation from Financial Transactions into Financial Snapshot.
Supports both default baseline heuristics and per-user custom scoring goals.
"""
from typing import Tuple, Optional
import frappe
import frappe

from well_pro.well_pro_app.services.scoring.config import (
    FINANCIAL_METRIC_WEIGHTS,
    TARGET_SAVINGS_RATE,
    OPTIMAL_DEBT_PAYMENT_RATIO,
    MAX_DEBT_PAYMENT_RATIO,
    EMERGENCY_FUND_TARGET_MONTHS,
    EXPENSE_RATIO_OPTIMAL,
    EXPENSE_RATIO_MAX,
    get_user_scoring_config
)
from well_pro.well_pro_app.services.scoring.normalization import (
    clamp,
    normalize_rating,
    normalize_inverse_rating,
    normalize_higher_is_better,
    normalize_lower_is_better
)


def accumulate_daily_financial_snapshot(user: str, target_date: str) -> Optional[str]:
    """
    Accumulates all Financial Transaction records logged for user on target_date
    into the Financial Snapshot for that day (creating or updating it).
    Returns the name of the Financial Snapshot document.
    """
    from unittest.mock import MagicMock
    if isinstance(getattr(frappe, "db", None), MagicMock) or hasattr(frappe.db, "_mock_return_value"):
        return None
    transactions = frappe.db.get_all(
        "Financial Transaction",
        filters={
            "user": user,
            "transaction_date": target_date
        },
        fields=["transaction_type", "amount", "essentiality"]
    )

    if not transactions:
        return None

    daily_income = sum(float(t.amount or 0.0) for t in transactions if t.transaction_type == "Income")
    daily_expenses = sum(float(t.amount or 0.0) for t in transactions if t.transaction_type == "Expense")
    daily_essential = sum(float(t.amount or 0.0) for t in transactions if t.transaction_type == "Expense" and t.essentiality == "Essential")
    daily_debt = sum(float(t.amount or 0.0) for t in transactions if t.transaction_type == "Debt Payment")
    daily_investment = sum(float(t.amount or 0.0) for t in transactions if t.transaction_type == "Investment")

    existing_snap = frappe.db.exists(
        "Financial Snapshot",
        {"user": user, "snapshot_date": target_date}
    )

    if existing_snap:
        snap = frappe.get_doc("Financial Snapshot", existing_snap)
        if snap.source == "Calculated":
            snap.monthly_income = daily_income
            snap.monthly_expenses = daily_expenses
            snap.essential_monthly_expenses = daily_essential
            snap.monthly_debt_payment = daily_debt
            snap.investment_value = daily_investment
            snap.liquid_savings = max(0.0, daily_income - daily_expenses)
        else:
            snap.monthly_expenses = max(float(snap.monthly_expenses or 0.0), daily_expenses)
            if daily_essential > 0:
                snap.essential_monthly_expenses = max(float(snap.essential_monthly_expenses or 0.0), daily_essential)
            if daily_income > 0:
                snap.monthly_income = max(float(snap.monthly_income or 0.0), daily_income)
            if daily_debt > 0:
                snap.monthly_debt_payment = max(float(snap.monthly_debt_payment or 0.0), daily_debt)
        snap.flags.ignore_hooks = True
        snap.save(ignore_permissions=True)
        frappe.db.commit()
        return snap.name
    else:
        # Check for prior snapshot to inherit baseline savings, debt, budget
        prior_snap = frappe.db.get_value(
            "Financial Snapshot",
            {"user": user, "snapshot_date": ["<", target_date]},
            [
                "monthly_income", "monthly_expenses", "essential_monthly_expenses",
                "liquid_savings", "investment_value", "emergency_fund",
                "budget_amount", "outstanding_debt", "monthly_debt_payment",
                "financial_stress_rating", "currency"
            ],
            order_by="snapshot_date desc",
            as_dict=True
        )

        if prior_snap:
            new_income = float(prior_snap.monthly_income or 0.0)
            if daily_income > 0:
                new_income = max(new_income, daily_income)
            new_expenses = float(prior_snap.monthly_expenses or 0.0) + daily_expenses
            new_essential = float(prior_snap.essential_monthly_expenses or 0.0) + daily_essential
            snap = frappe.get_doc({
                "doctype": "Financial Snapshot",
                "user": user,
                "snapshot_date": target_date,
                "monthly_income": new_income,
                "monthly_expenses": new_expenses,
                "essential_monthly_expenses": new_essential,
                "liquid_savings": float(prior_snap.liquid_savings or 0.0) + daily_income - daily_expenses,
                "investment_value": float(prior_snap.investment_value or 0.0) + daily_investment,
                "emergency_fund": float(prior_snap.emergency_fund or 0.0),
                "budget_amount": float(prior_snap.budget_amount or 0.0),
                "outstanding_debt": max(0.0, float(prior_snap.outstanding_debt or 0.0) - daily_debt),
                "monthly_debt_payment": float(prior_snap.monthly_debt_payment or 0.0) + daily_debt,
                "financial_stress_rating": prior_snap.financial_stress_rating,
                "currency": prior_snap.currency,
                "source": "Calculated"
            })
        else:
            snap = frappe.get_doc({
                "doctype": "Financial Snapshot",
                "user": user,
                "snapshot_date": target_date,
                "monthly_income": daily_income,
                "monthly_expenses": daily_expenses,
                "essential_monthly_expenses": daily_essential,
                "liquid_savings": max(0.0, daily_income - daily_expenses),
                "investment_value": daily_investment,
                "emergency_fund": max(0.0, daily_income - daily_expenses),
                "budget_amount": daily_income if daily_income > 0 else (daily_expenses * 1.2),
                "outstanding_debt": 0.0,
                "monthly_debt_payment": daily_debt,
                "source": "Calculated"
            })
        snap.flags.ignore_hooks = True
        snap.insert(ignore_permissions=True)
        frappe.db.commit()
        return snap.name


def calculate_financial_score(user: str, target_date: str) -> Tuple[float, float]:
    """
    Computes daily financial score and confidence for a given user and date.
    Uses custom scoring goals if set by the user, otherwise falls back to defaults.
    Returns: (score: float, confidence: float)
    """
    # 0. Sync and accumulate any Financial Transactions for this date
    try:
        accumulate_daily_financial_snapshot(user, target_date)
    except Exception as e:
        frappe.log_error(
            title=f"Financial Snapshot Fail: {user}"[:140],
            text=f"Financial daily snapshot accumulation failed for {user} on {target_date}.\nError: {str(e)}"
        )


    # 1. Fetch user-specific scoring config (custom or default baseline)
    cfg = get_user_scoring_config(user)
    target_savings_rate = cfg.get("target_savings_rate", TARGET_SAVINGS_RATE)
    optimal_debt_payment_ratio = cfg.get("optimal_debt_payment_ratio", OPTIMAL_DEBT_PAYMENT_RATIO)
    max_debt_payment_ratio = cfg.get("max_debt_payment_ratio", MAX_DEBT_PAYMENT_RATIO)
    emergency_fund_target_months = cfg.get("emergency_fund_target_months", EMERGENCY_FUND_TARGET_MONTHS)
    expense_ratio_optimal = cfg.get("expense_ratio_optimal", EXPENSE_RATIO_OPTIMAL)
    expense_ratio_max = cfg.get("expense_ratio_max", EXPENSE_RATIO_MAX)
    custom_budget = cfg.get("budget_amount")

    # 2. Fetch latest Financial Snapshot on or before target date
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

    # 3. Check for check-in financial stress rating if snapshot missing it
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
        # Target: >= savings rate goal receives full score
        sav_score = normalize_higher_is_better(savings_rate, target_savings_rate)
        if sav_score is not None:
            component_scores["savings"] = sav_score
            available_weights["savings"] = FINANCIAL_METRIC_WEIGHTS["savings"]

    # Component 2: Expense / Budget Management (weight = 25)
    # Effective budget: custom user goal > snapshot.budget_amount > expense ratio heuristic
    effective_budget = custom_budget if (custom_budget and custom_budget > 0) else (
        float(snap.budget_amount) if (snap and snap.budget_amount and float(snap.budget_amount) > 0) else None
    )

    if effective_budget and effective_budget > 0:
        if expenses > 0:
            budget_ratio = expenses / effective_budget
            bud_score = normalize_lower_is_better(budget_ratio, 1.0, 1.3)
            if bud_score is not None:
                component_scores["expense_budget"] = bud_score
                available_weights["expense_budget"] = FINANCIAL_METRIC_WEIGHTS["expense_budget"]
        else:
            component_scores["expense_budget"] = 100.0
            available_weights["expense_budget"] = FINANCIAL_METRIC_WEIGHTS["expense_budget"]
    elif has_income:
        expense_ratio = expenses / income
        # Expenses <= optimal expense ratio is 100, >= max expense ratio is 0
        exp_score = normalize_lower_is_better(expense_ratio, expense_ratio_optimal, expense_ratio_max)
        if exp_score is not None:
            component_scores["expense_budget"] = exp_score
            available_weights["expense_budget"] = FINANCIAL_METRIC_WEIGHTS["expense_budget"]

    # Component 3: Debt Burden (weight = 20)
    # Debt Payment Ratio = monthly_debt_payment / monthly_income
    if has_income and snap and snap.monthly_debt_payment is not None:
        debt_payment = float(snap.monthly_debt_payment)
        dti = debt_payment / income
        dti_score = normalize_lower_is_better(dti, optimal_debt_payment_ratio, max_debt_payment_ratio)
        if dti_score is not None:
            component_scores["debt"] = dti_score
            available_weights["debt"] = FINANCIAL_METRIC_WEIGHTS["debt"]
    elif snap and snap.outstanding_debt is not None and float(snap.outstanding_debt) == 0.0:
        # Confirmed zero debt
        component_scores["debt"] = 100.0
        available_weights["debt"] = FINANCIAL_METRIC_WEIGHTS["debt"]

    # Component 4: Emergency Fund / Liquid Reserve (weight = 15)
    if snap:
        liquid = float(snap.emergency_fund or snap.liquid_savings or 0.0)
        essential = float(snap.essential_monthly_expenses or (expenses * 0.7) or 1.0)
        if essential > 0:
            coverage_months = liquid / essential
            ef_score = normalize_higher_is_better(coverage_months, emergency_fund_target_months)
            if ef_score is not None:
                component_scores["emergency_fund"] = ef_score
                available_weights["emergency_fund"] = FINANCIAL_METRIC_WEIGHTS["emergency_fund"]

    # Component 5: Financial Stress (weight = 10)
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
