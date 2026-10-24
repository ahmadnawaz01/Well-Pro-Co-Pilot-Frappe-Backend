"""
WellPro Top-Level API Compatibility Layer
Aliases endpoints to well_pro.well_pro_app.api for backward compatibility.
"""
import frappe
from well_pro.well_pro_app.api import (
    signup,
    login,
    verify_user_session,
    insert_record,
    store_ai_record,
    update_record,
    delete_record,
    get_user_records,
    get_dashboard,
    get_dashboard_metrics,
    recalculate_score,
    success_response,
    error_response
)

__all__ = [
    "signup",
    "login",
    "verify_user_session",
    "insert_record",
    "store_ai_record",
    "update_record",
    "delete_record",
    "get_user_records",
    "get_dashboard",
    "get_dashboard_metrics",
    "recalculate_score",
    "success_response",
    "error_response"
]
