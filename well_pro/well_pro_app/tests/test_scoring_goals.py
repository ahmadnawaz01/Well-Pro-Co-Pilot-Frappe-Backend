"""
Unit and Integration Tests for Custom Scoring Goals and Scale Conversion.
Tests:
- Goal scale conversion ('10k' -> 10000, '$10,000' -> 10000.0, '20%' -> 0.20, '2500ml' -> 2.5L, '1h' -> 60m)
- Fallback to original default config when goals are not set
- setup_scoring_goals API endpoint with human-friendly and numeric inputs
- Dynamic scoring engine adjustment based on user custom goals
- Multi-user isolation (User A cannot modify User B's goals without admin role)
- Reset functionality restoring original baseline heuristics
"""
import frappe
from frappe.tests.utils import FrappeTestCase
from well_pro.well_pro_app.services.scoring.config import (
    DEFAULT_SCORING_CONFIG,
    STEPS_TARGET,
    TARGET_SAVINGS_RATE,
    convert_goal_to_config_scale,
    parse_custom_goals,
    get_user_custom_goals,
    get_user_scoring_config
)
from well_pro.well_pro_app.services.scoring.health import calculate_health_score
from well_pro.well_pro_app.services.scoring.financial import calculate_financial_score
from well_pro.well_pro_app.api import (
    setup_scoring_goals,
    set_scoring_goals,
    get_scoring_goals
)


class TestScoringGoals(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.user_a = "user_a@wellpro.test"
        self.user_b = "user_b@wellpro.test"

        for u in [self.user_a, self.user_b]:
            if not frappe.db.exists("User", u):
                user_doc = frappe.get_doc({
                    "doctype": "User",
                    "email": u,
                    "first_name": u.split("@")[0],
                    "enabled": 1,
                    "user_type": "System User"
                }).insert(ignore_permissions=True)
                user_doc.new_password = "Password123!"
                user_doc.save(ignore_permissions=True)

            if not frappe.db.exists("WellPro Profile", {"user": u}):
                frappe.get_doc({"doctype": "WellPro Profile", "user": u}).insert(ignore_permissions=True)
            else:
                p_name = frappe.db.get_value("WellPro Profile", {"user": u}, "name")
                frappe.db.set_value("WellPro Profile", p_name, "custom_scoring_goals", "{}")

            frappe.db.delete("Health Daily Record", {"user": u})
            frappe.db.delete("Financial Snapshot", {"user": u})
            frappe.db.delete("Wellbeing Daily Score", {"user": u})

        frappe.db.commit()

    def tearDown(self):
        frappe.set_user("Administrator")

    def test_goal_scale_conversions(self):
        """Validates that various human-friendly representations convert accurately to config scale."""
        # Steps conversions
        _, steps_k = convert_goal_to_config_scale("steps", "10k")
        self.assertEqual(steps_k, 10000)
        _, steps_raw = convert_goal_to_config_scale("steps_target", 12500)
        self.assertEqual(steps_raw, 12500)
        _, steps_str = convert_goal_to_config_scale("daily_steps", "8,000")
        self.assertEqual(steps_str, 8000)

        # Financial Budget conversions
        _, budget_k = convert_goal_to_config_scale("financial_budget", "10k")
        self.assertEqual(budget_k, 10000.0)
        _, budget_dollar = convert_goal_to_config_scale("budget", "$10,000")
        self.assertEqual(budget_dollar, 10000.0)
        _, budget_float = convert_goal_to_config_scale("budget_amount", 7500.50)
        self.assertEqual(budget_float, 7500.50)

        # Savings rate / percentage conversions
        _, sav_pct = convert_goal_to_config_scale("savings_rate", "20%")
        self.assertEqual(sav_pct, 0.20)
        _, sav_100 = convert_goal_to_config_scale("target_savings_rate", 25)
        self.assertEqual(sav_100, 0.25)
        _, sav_dec = convert_goal_to_config_scale("savings_rate", 0.18)
        self.assertEqual(sav_dec, 0.18)

        # Volume / Hydration
        _, water_ml = convert_goal_to_config_scale("water", "2500ml")
        self.assertEqual(water_ml, 2.5)
        _, water_l = convert_goal_to_config_scale("water_liters_target", "3L")
        self.assertEqual(water_l, 3.0)

        # Time conversions
        _, ex_h = convert_goal_to_config_scale("exercise_minutes", "1h")
        self.assertEqual(ex_h, 60)
        _, ex_m = convert_goal_to_config_scale("exercise_minutes_target", "45 mins")
        self.assertEqual(ex_m, 45)
        _, sleep_h = convert_goal_to_config_scale("sleep_min", "7.5h")
        self.assertEqual(sleep_h, 7.5)

    def test_default_config_applied_when_no_custom_goals(self):
        """If a user has not configured goals, the original config heuristics apply."""
        frappe.set_user(self.user_a)
        cfg = get_user_scoring_config(self.user_a)

        self.assertEqual(cfg["steps_target"], STEPS_TARGET)
        self.assertEqual(cfg["target_savings_rate"], TARGET_SAVINGS_RATE)
        self.assertIsNone(cfg["budget_amount"])

    def test_setup_scoring_goals_api_endpoint(self):
        """User A can configure custom goals like 10000 steps and 10k budget via API."""
        frappe.set_user(self.user_a)

        # Setup custom goals: steps = 8k, financial budget = 10k, savings rate = 25%
        res = setup_scoring_goals(
            steps="8k",
            financial_budget="10k",
            savings_rate="25%",
            recalculate=False
        )

        self.assertTrue(res["success"])
        data = res["data"]
        self.assertEqual(data["user"], self.user_a)
        self.assertEqual(data["configured_goals"]["steps_target"], 8000)
        self.assertEqual(data["configured_goals"]["budget_amount"], 10000.0)
        self.assertEqual(data["configured_goals"]["target_savings_rate"], 0.25)

        # Effective config has new custom values merged over default heuristics
        cfg = get_user_scoring_config(self.user_a)
        self.assertEqual(cfg["steps_target"], 8000)
        self.assertEqual(cfg["budget_amount"], 10000.0)
        self.assertEqual(cfg["target_savings_rate"], 0.25)
        # Non-customized heuristics remain at original defaults
        self.assertEqual(cfg["active_minutes_target"], DEFAULT_SCORING_CONFIG["active_minutes_target"])

    def test_scoring_engine_applies_custom_goals(self):
        """Scoring engine calculates scores against user's custom goals."""
        frappe.set_user(self.user_a)
        test_date = "2026-10-24"

        # Log complete health record for user A with 8000 steps
        frappe.get_doc({
            "doctype": "Health Daily Record",
            "user": self.user_a,
            "record_date": test_date,
            "sleep_hours": 8.0,
            "sleep_quality": 5,
            "steps": 8000,
            "active_minutes": 30,
            "exercise_minutes": 45,
            "water_liters": 2.5,
            "calories_consumed": 2000.0,
            "protein_grams": 60.0,
            "fruit_veg_servings": 5.0,
            "energy_level": 5,
            "self_rated_health": 5
        }).insert(ignore_permissions=True)

        # Without custom goal (default target = 10000), 8000 steps yields ~98.5
        score_default, _ = calculate_health_score(self.user_a, test_date)
        self.assertAlmostEqual(score_default, 98.5, places=1)

        # User A sets custom goal of 8000 steps (8k)
        setup_scoring_goals(steps="8k", recalculate=False)

        # With custom target = 8000, 8000 steps achieves full score 100.0
        score_custom, _ = calculate_health_score(self.user_a, test_date)
        self.assertEqual(score_custom, 100.0)
        self.assertGreater(score_custom, score_default)

    def test_custom_financial_budget_scoring(self):
        """User A setting a financial budget of 10k has expenses evaluated against that budget."""
        frappe.set_user(self.user_a)
        test_date = "2026-10-24"

        # Set custom financial budget of 10k
        setup_scoring_goals(financial_budget="10k", recalculate=False)

        # Create snapshot with monthly expenses = 8000 (no income)
        frappe.get_doc({
            "doctype": "Financial Snapshot",
            "user": self.user_a,
            "snapshot_date": test_date,
            "monthly_income": 0.0,
            "monthly_expenses": 8000.0,
            "outstanding_debt": 0.0
        }).insert(ignore_permissions=True)

        score, conf = calculate_financial_score(self.user_a, test_date)
        # Expense is 8000 <= 10000 (ratio 0.8 <= 1.0), so expense budget scores 100.0
        self.assertGreater(score, 0)
        self.assertGreater(conf, 0)

    def test_multi_user_isolation_for_scoring_goals(self):
        """User A cannot modify or view User B's scoring goals."""
        frappe.set_user(self.user_a)

        # User A attempts to set scoring goals for User B
        with self.assertRaises(frappe.PermissionError):
            setup_scoring_goals(steps="15k", target_user=self.user_b)

        # User A attempts to read User B's scoring goals
        with self.assertRaises(frappe.PermissionError):
            get_scoring_goals(target_user=self.user_b)

    def test_reset_scoring_goals_restores_defaults(self):
        """Calling setup_scoring_goals with reset=True clears custom goals."""
        frappe.set_user(self.user_a)

        # Set custom goals
        setup_scoring_goals(steps="12k", financial_budget="15k", recalculate=False)
        self.assertEqual(get_user_scoring_config(self.user_a)["steps_target"], 12000)

        # Reset custom goals
        reset_res = setup_scoring_goals(reset=True, recalculate=False)
        self.assertTrue(reset_res["success"])

        # Config reverts back to default
        cfg = get_user_scoring_config(self.user_a)
        self.assertEqual(cfg["steps_target"], STEPS_TARGET)
        self.assertIsNone(cfg["budget_amount"])
