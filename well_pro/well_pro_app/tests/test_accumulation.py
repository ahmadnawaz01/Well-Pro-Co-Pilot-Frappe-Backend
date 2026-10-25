"""
Frappe Integration Test for Same-Day Record Accumulation & Dashboard Scores.
Verifies that:
- Multiple same-day Health Activity records accumulate steps, exercise minutes into daily total record
- Multiple same-day Financial Transactions accumulate into daily total record (Financial Snapshot)
- recalculate_score computes fresh scores reflecting accumulated data
- get_dashboard returns newly calculated results
"""
import frappe
from frappe.tests.utils import FrappeTestCase
from well_pro.well_pro_app.api import insert_record, recalculate_score, get_dashboard


class TestRecordAccumulation(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.user = "test_accum@wellpro.test"
        self.target_date = "2026-10-25"

        if not frappe.db.exists("User", self.user):
            user_doc = frappe.get_doc({
                "doctype": "User",
                "email": self.user,
                "first_name": "AccumTest",
                "enabled": 1,
                "user_type": "System User"
            }).insert(ignore_permissions=True)
            user_doc.new_password = "Password123!"
            user_doc.save(ignore_permissions=True)

        if not frappe.db.exists("WellPro Profile", {"user": self.user}):
            frappe.get_doc({"doctype": "WellPro Profile", "user": self.user}).insert(ignore_permissions=True)
        if not frappe.db.exists("User Consent Preference", {"user": self.user}):
            frappe.get_doc({"doctype": "User Consent Preference", "user": self.user}).insert(ignore_permissions=True)

        # Clear records for target_date to test clean accumulation
        frappe.db.delete("Health Activity", {"user": self.user})
        frappe.db.delete("Health Daily Record", {"user": self.user})
        frappe.db.delete("Financial Transaction", {"user": self.user})
        frappe.db.delete("Financial Snapshot", {"user": self.user})
        frappe.db.delete("Wellbeing Daily Score", {"user": self.user})
        frappe.db.commit()

    def tearDown(self):
        frappe.set_user("Administrator")

    def test_same_day_health_activity_accumulation(self):
        """Adding multiple Health Activities on the same day must accumulate into Health Daily Record."""
        frappe.set_user(self.user)

        # 1. Log First Activity: 3000 steps, 30 min
        res1 = insert_record("Health Activity", {
            "activity_type": "Running",
            "logged_at": f"{self.target_date} 07:30:00",
            "duration_minutes": 30.0,
            "steps": 3000,
            "calories_burned": 250.0,
            "source": "Wearable"
        })
        self.assertTrue(res1["success"])

        hdr = frappe.db.get_value(
            "Health Daily Record",
            {"user": self.user, "record_date": self.target_date},
            ["steps", "exercise_minutes"],
            as_dict=True
        )
        self.assertIsNotNone(hdr)
        self.assertEqual(hdr.steps, 3000)
        self.assertEqual(hdr.exercise_minutes, 30)

        # 2. Log Second Activity on same day: 2500 steps, 25 min
        res2 = insert_record("Health Activity", {
            "activity_type": "Walking",
            "logged_at": f"{self.target_date} 18:30:00",
            "duration_minutes": 25.0,
            "steps": 2500,
            "calories_burned": 150.0,
            "source": "Wearable"
        })
        self.assertTrue(res2["success"])

        # Must accumulate: 3000 + 2500 = 5500 steps, 30 + 25 = 55 min
        hdr2 = frappe.db.get_value(
            "Health Daily Record",
            {"user": self.user, "record_date": self.target_date},
            ["steps", "exercise_minutes"],
            as_dict=True
        )
        self.assertEqual(hdr2.steps, 5500)
        self.assertEqual(hdr2.exercise_minutes, 55)

    def test_same_day_financial_transaction_accumulation(self):
        """Adding multiple Financial Transactions on the same day must accumulate into Financial Snapshot."""
        frappe.set_user(self.user)

        cat_groceries = frappe.db.get_value("Financial Category", {"category_name": "Groceries & Food"}, "name") or "Groceries & Food"
        cat_dining = frappe.db.get_value("Financial Category", {"category_name": "Dining & Social"}, "name") or "Dining & Social"
        cat_salary = frappe.db.get_value("Financial Category", {"category_name": "Salary & Wages"}, "name") or "Salary & Wages"

        # 1. Log First Expense: $50 Essential
        res1 = insert_record("Financial Transaction", {
            "transaction_type": "Expense",
            "category": cat_groceries,
            "amount": 50.0,
            "transaction_date": self.target_date,
            "essentiality": "Essential",
            "source": "Manual Entry"
        })
        self.assertTrue(res1["success"])

        snap1 = frappe.db.get_value(
            "Financial Snapshot",
            {"user": self.user, "snapshot_date": self.target_date},
            ["monthly_expenses", "essential_monthly_expenses"],
            as_dict=True
        )
        self.assertIsNotNone(snap1)
        self.assertEqual(snap1.monthly_expenses, 50.0)
        self.assertEqual(snap1.essential_monthly_expenses, 50.0)

        # 2. Log Second Expense on same day: $30 Discretionary
        res2 = insert_record("Financial Transaction", {
            "transaction_type": "Expense",
            "category": cat_dining,
            "amount": 30.0,
            "transaction_date": self.target_date,
            "essentiality": "Discretionary",
            "source": "Manual Entry"
        })
        self.assertTrue(res2["success"])

        snap2 = frappe.db.get_value(
            "Financial Snapshot",
            {"user": self.user, "snapshot_date": self.target_date},
            ["monthly_expenses", "essential_monthly_expenses"],
            as_dict=True
        )
        self.assertEqual(snap2.monthly_expenses, 80.0)
        self.assertEqual(snap2.essential_monthly_expenses, 50.0)

        # 3. Log Income on same day: $2000
        res3 = insert_record("Financial Transaction", {
            "transaction_type": "Income",
            "category": cat_salary,
            "amount": 2000.0,
            "transaction_date": self.target_date,
            "source": "Manual Entry"
        })
        self.assertTrue(res3["success"])

        snap3 = frappe.db.get_value(
            "Financial Snapshot",
            {"user": self.user, "snapshot_date": self.target_date},
            ["monthly_income", "monthly_expenses", "liquid_savings"],
            as_dict=True
        )
        self.assertEqual(snap3.monthly_income, 2000.0)
        self.assertEqual(snap3.monthly_expenses, 80.0)
        self.assertEqual(snap3.liquid_savings, 1920.0)

    def test_recalculate_score_and_dashboard_reflect_accumulated_data(self):
        """Recalculate score and get_dashboard API must return freshly calculated results reflecting accumulations."""
        frappe.set_user(self.user)

        # Log activities and transactions
        cat_groceries = frappe.db.get_value("Financial Category", {"category_name": "Groceries & Food"}, "name") or "Groceries & Food"
        cat_salary = frappe.db.get_value("Financial Category", {"category_name": "Salary & Wages"}, "name") or "Salary & Wages"

        insert_record("Health Activity", {
            "activity_type": "Running",
            "logged_at": f"{self.target_date} 09:00:00",
            "duration_minutes": 45.0,
            "steps": 6000,
            "calories_burned": 400.0
        })

        insert_record("Financial Transaction", {
            "transaction_type": "Expense",
            "category": cat_groceries,
            "amount": 100.0,
            "transaction_date": self.target_date
        })

        insert_record("Financial Transaction", {
            "transaction_type": "Income",
            "category": cat_salary,
            "amount": 3000.0,
            "transaction_date": self.target_date
        })

        # Test recalculate_score
        recalc = recalculate_score(date=self.target_date)
        self.assertTrue(recalc["success"])
        recalc_data = recalc["data"]
        self.assertGreater(recalc_data["health_score"], 0)
        self.assertGreater(recalc_data["financial_score"], 0)
        self.assertGreater(recalc_data["overall_score"], 0)

        # Test get_dashboard
        dash = get_dashboard(as_of_date=self.target_date)
        self.assertTrue(dash["success"])
        dash_data = dash["data"]
        self.assertEqual(dash_data["health"]["today_score"], recalc_data["health_score"])
        self.assertEqual(dash_data["financial"]["today_score"], recalc_data["financial_score"])
        self.assertEqual(dash_data["overall"]["today_score"], recalc_data["overall_score"])
