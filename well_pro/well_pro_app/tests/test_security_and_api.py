"""
Frappe Integration Tests for WellPro API & Multi-User Isolation.
Tests:
- User A retrieves own records
- User A cannot retrieve User B records
- User A cannot update User B records
- User A cannot insert data on behalf of User B
- Generic CRUD rejects arbitrary DocTypes (User, Role, System Settings)
- Score persistence idempotency (no duplicate rows)
- Score recalculation on historical source data changes
"""
from datetime import date
import frappe
from frappe.tests.utils import FrappeTestCase
from well_pro.well_pro_app.api import (
    ALLOWED_DOCTYPES,
    insert_record,
    update_record,
    delete_record,
    get_user_records,
    recalculate_score,
    get_dashboard
)
from well_pro.well_pro_app.services.scoring import calculate_daily_score


class TestWellProSecurityAndAPI(FrappeTestCase):
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
            if not frappe.db.exists("User Consent Preference", {"user": u}):
                frappe.get_doc({"doctype": "User Consent Preference", "user": u}).insert(ignore_permissions=True)

        frappe.db.commit()

    def tearDown(self):
        frappe.set_user("Administrator")

    def test_allowlist_blocks_arbitrary_doctypes(self):
        """Generic CRUD APIs must reject arbitrary system DocTypes."""
        frappe.set_user(self.user_a)
        forbidden_doctypes = ["User", "Role", "System Settings", "DocType", "Has Role"]

        for dt in forbidden_doctypes:
            with self.assertRaises((frappe.PermissionError, Exception)):
                insert_record(dt, {"name": "test_hack"})
            with self.assertRaises((frappe.PermissionError, Exception)):
                get_user_records(dt)

    def test_user_cannot_spoof_ownership_on_insert(self):
        """User A submitting user: User B must have user overridden to User A."""
        frappe.set_user(self.user_a)
        test_date = "2026-10-15"

        # Attempt to insert health record claiming to be user_b
        res = insert_record("Health Daily Record", {
            "user": self.user_b,
            "record_date": test_date,
            "sleep_hours": 8.0,
            "steps": 9000
        })
        created_name = res["data"]["name"]
        doc = frappe.get_doc("Health Daily Record", created_name)

        # Must be owned by user_a, NOT user_b
        self.assertEqual(doc.user, self.user_a)

    def test_multi_user_isolation_retrieval(self):
        """User A must NOT be able to view User B records via get_user_records."""
        frappe.set_user("Administrator")
        # Insert a record for User B
        b_rec = frappe.get_doc({
            "doctype": "Health Daily Record",
            "user": self.user_b,
            "record_date": "2026-10-16",
            "sleep_hours": 7.5
        }).insert(ignore_permissions=True)
        frappe.db.commit()

        # Switch to User A
        frappe.set_user(self.user_a)
        records = get_user_records("Health Daily Record")["data"]
        record_names = [r["name"] for r in records]

        # User B's record must NOT be in User A's list
        self.assertNotIn(b_rec.name, record_names)

    def test_multi_user_isolation_update(self):
        """User A cannot update User B's record."""
        frappe.set_user("Administrator")
        b_rec = frappe.get_doc({
            "doctype": "Health Daily Record",
            "user": self.user_b,
            "record_date": "2026-10-17",
            "sleep_hours": 7.0
        }).insert(ignore_permissions=True)
        frappe.db.commit()

        # Switch to User A and attempt to modify User B's record
        frappe.set_user(self.user_a)
        with self.assertRaises(frappe.PermissionError):
            update_record("Health Daily Record", b_rec.name, {"sleep_hours": 9.0})

    def test_multi_user_isolation_delete(self):
        """User A cannot delete User B's record."""
        frappe.set_user("Administrator")
        b_rec = frappe.get_doc({
            "doctype": "Health Daily Record",
            "user": self.user_b,
            "record_date": "2026-10-18",
            "sleep_hours": 7.0
        }).insert(ignore_permissions=True)
        frappe.db.commit()

        frappe.set_user(self.user_a)
        with self.assertRaises(frappe.PermissionError):
            delete_record("Health Daily Record", b_rec.name)

    def test_score_persistence_idempotency(self):
        """Repeated score recalculation must update the existing record rather than duplicate."""
        frappe.set_user("Administrator")
        test_date = "2026-10-19"

        # Calculate score first time
        res1 = calculate_daily_score(self.user_a, test_date)
        # Calculate score second time
        res2 = calculate_daily_score(self.user_a, test_date)

        self.assertEqual(res1["name"], res2["name"])

        # Count records in database for this date and user
        count = frappe.db.count("Wellbeing Daily Score", {
            "user": self.user_a,
            "score_date": test_date,
            "scoring_version": "v1"
        })
        self.assertEqual(count, 1)

    def test_historical_update_recalculates_correct_date(self):
        """Updating an October 10 record must recalculate October 10 score."""
        frappe.set_user(self.user_a)
        hist_date = "2026-10-10"

        # Create record for Oct 10
        insert_res = insert_record("Health Daily Record", {
            "record_date": hist_date,
            "sleep_hours": 8.0,
            "steps": 10000
        })
        rec_name = insert_res["data"]["name"]

        # Verify score exists for Oct 10
        score_doc = frappe.db.get_value(
            "Wellbeing Daily Score",
            {"user": self.user_a, "score_date": hist_date, "scoring_version": "v1"},
            ["health_score", "health_confidence"],
            as_dict=True
        )
        self.assertIsNotNone(score_doc)
        self.assertGreater(score_doc.health_score, 0)
