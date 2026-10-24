"""
WellPro Scheduled Background Tasks
"""
import frappe
from frappe.utils import today
from well_pro.well_pro_app.services.scoring import calculate_daily_score

def run_nightly_wellbeing_scoring():
    """Background daily cron job calculating wellbeing scores for all active users."""
    users = frappe.get_all("User", filters={"enabled": 1, "user_type": "System User"}, fields=["name"])
    calc_date = today()
    for u in users:
        try:
            calculate_daily_score(u.name, calc_date)
        except Exception as e:
            frappe.log_error(
                f"Nightly scoring error for user {u.name} on {calc_date}: {str(e)}",
                "WellPro Nightly Scoring Failure"
            )
