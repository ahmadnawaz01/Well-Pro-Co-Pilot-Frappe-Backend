"""
Unit tests for domain scoring engines: Health, Financial, Social, and Overall.
Binds frappe.local.db with MagicMock so tests can execute without a running bench site.
"""
import unittest
from unittest.mock import MagicMock
import frappe
from frappe import _dict

from well_pro.well_pro_app.services.scoring.health import calculate_health_score
from well_pro.well_pro_app.services.scoring.financial import calculate_financial_score
from well_pro.well_pro_app.services.scoring.social import calculate_social_score
from well_pro.well_pro_app.services.scoring.aggregation import calculate_overall_score


class TestScoringEngine(unittest.TestCase):
    def setUp(self):
        # Bind frappe.local and frappe.local.db so frappe.db proxy resolves without MariaDB
        frappe.local.db = MagicMock()

    def test_health_score_complete_data(self):
        frappe.local.db.get_value.return_value = _dict({
            "sleep_hours": 8.0,
            "sleep_quality": 5,
            "steps": 10000,
            "active_minutes": 30,
            "exercise_minutes": 45,
            "water_liters": 2.5,
            "calories_consumed": 2000.0,
            "protein_grams": 60.0,
            "fruit_veg_servings": 5.0,
            "energy_level": 5,
            "self_rated_health": 5
        })
        frappe.local.db.get_all.return_value = []

        score, conf = calculate_health_score("test@wellpro.test", "2026-10-23")
        self.assertEqual(score, 100.0)
        self.assertEqual(conf, 100.0)

    def test_health_score_partial_data_renormalization(self):
        frappe.local.db.get_value.return_value = _dict({
            "sleep_hours": 8.0,
            "sleep_quality": 5,
            "steps": None,
            "active_minutes": None,
            "exercise_minutes": None,
            "water_liters": None,
            "calories_consumed": None,
            "protein_grams": None,
            "fruit_veg_servings": None,
            "energy_level": None,
            "self_rated_health": None
        })
        frappe.local.db.get_all.return_value = []

        score, conf = calculate_health_score("test@wellpro.test", "2026-10-23")
        self.assertEqual(score, 100.0)
        self.assertEqual(conf, 30.0)

    def test_health_score_missing_data(self):
        frappe.local.db.get_value.return_value = None
        frappe.local.db.get_all.return_value = []

        score, conf = calculate_health_score("test@wellpro.test", "2026-10-23")
        self.assertEqual(score, 0.0)
        self.assertEqual(conf, 0.0)

    def test_financial_score_healthy_snapshot(self):
        def side_effect(doctype, *args, **kwargs):
            if doctype == "Financial Snapshot":
                return _dict({
                    "monthly_income": 10000.0,
                    "monthly_expenses": 6000.0,
                    "essential_monthly_expenses": 4000.0,
                    "liquid_savings": 36000.0,
                    "investment_value": 50000.0,
                    "emergency_fund": 36000.0,
                    "budget_amount": 6500.0,
                    "outstanding_debt": 5000.0,
                    "monthly_debt_payment": 1000.0,
                    "financial_stress_rating": 1
                })
            return None

        frappe.local.db.get_value.side_effect = side_effect

        score, conf = calculate_financial_score("test@wellpro.test", "2026-10-23")
        self.assertEqual(score, 100.0)
        self.assertEqual(conf, 100.0)

    def test_financial_score_missing_income(self):
        def side_effect(doctype, *args, **kwargs):
            if doctype == "Financial Snapshot":
                return _dict({
                    "monthly_income": None,
                    "monthly_expenses": 3000.0,
                    "essential_monthly_expenses": 2000.0,
                    "liquid_savings": 12000.0,
                    "investment_value": 0.0,
                    "emergency_fund": 12000.0,
                    "budget_amount": None,
                    "outstanding_debt": 0.0,
                    "monthly_debt_payment": None,
                    "financial_stress_rating": 2
                })
            return None

        frappe.local.db.get_value.side_effect = side_effect

        score, conf = calculate_financial_score("test@wellpro.test", "2026-10-23")
        self.assertGreater(score, 0.0)
        self.assertLess(conf, 100.0)
        self.assertGreater(conf, 0.0)

    def test_financial_score_no_data(self):
        frappe.local.db.get_value.side_effect = None
        frappe.local.db.get_value.return_value = None
        score, conf = calculate_financial_score("test@wellpro.test", "2026-10-23")
        self.assertEqual(score, 0.0)
        self.assertEqual(conf, 0.0)

    def test_social_score_complete(self):
        frappe.local.db.get_all.return_value = [
            _dict({"interaction_quality": 5, "connection_level": 5, "mood_after": 5})
        ]
        frappe.local.db.get_value.side_effect = None
        frappe.local.db.get_value.return_value = _dict({
            "mood": 5,
            "social_connection": 5,
            "loneliness": 1,
            "social_satisfaction": 5
        })

        score, conf = calculate_social_score("test@wellpro.test", "2026-10-23")
        self.assertEqual(score, 100.0)
        self.assertEqual(conf, 100.0)

    def test_social_score_loneliness_inversion(self):
        frappe.local.db.get_all.return_value = []
        frappe.local.db.get_value.side_effect = None
        frappe.local.db.get_value.return_value = _dict({
            "mood": 3,
            "social_connection": 3,
            "loneliness": 5,
            "social_satisfaction": 3
        })

        score, conf = calculate_social_score("test@wellpro.test", "2026-10-23")
        self.assertLess(score, 50.0)
        self.assertGreater(conf, 0.0)

    def test_social_score_no_data(self):
        frappe.local.db.get_all.return_value = []
        frappe.local.db.get_value.side_effect = None
        frappe.local.db.get_value.return_value = None

        score, conf = calculate_social_score("test@wellpro.test", "2026-10-23")
        self.assertEqual(score, 0.0)
        self.assertEqual(conf, 0.0)


if __name__ == "__main__":
    unittest.main()
