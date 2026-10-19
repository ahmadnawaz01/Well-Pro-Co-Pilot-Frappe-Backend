import frappe
from frappe import _

@frappe.whitelist(allow_guest=False)
def verify_user_session():
    """
    Validates that the caller is an authenticated Frappe user.
    Returns basic user details to FastAPI or React.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Unauthorized access"), frappe.AuthenticationError)
        
    user_doc = frappe.get_doc("User", user)
    return {
        "status": "success",
        "user": user,
        "full_name": user_doc.full_name,
        "email": user_doc.email
    }


@frappe.whitelist(allow_guest=False)
def store_ai_record(domain, record_data):
    """
    Endpoint for FastAPI to store structured AI output into Frappe.
    Supports 'financial', 'health', and 'wellbeing' domains.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Unauthorized access"), frappe.AuthenticationError)

    if isinstance(record_data, str):
        import json
        record_data = json.loads(record_data)

    if domain == "financial":
        doctype = "Financial Record"
    elif domain == "health":
        doctype = "Health Record"
    elif domain == "wellbeing":
        doctype = "Wellbeing Record"
    else:
        frappe.throw(_("Invalid domain provided"))

    doc = frappe.get_doc({
        "doctype": doctype,
        **record_data,
        "owner": user
    })
    doc.insert(ignore_permissions=False)
    frappe.db.commit()

    return {
        "status": "success",
        "message": f"Saved to {doctype}",
        "name": doc.name
    }


@frappe.whitelist(allow_guest=False)
def get_dashboard_metrics():
    """
    Calculates aggregated statistics for the Three-Dimension Dashboard.
    """
    user = frappe.session.user

    # 1. Financial Totals
    financial_summary = frappe.db.sql("""
        SELECT transaction_type, SUM(amount) as total
        FROM `tabFinancial Record`
        WHERE owner = %s
        GROUP BY transaction_type
    """, (user,), as_dict=True)

    # 2. Health Highlights
    health_records = frappe.get_all(
        "Health Record",
        filters={"owner": user},
        fields=["health_type", "title", "value_quantity", "unit", "logged_at"],
        order_by="logged_at desc",
        limit=10
    )

    # 3. Wellbeing Highlights
    wellbeing_records = frappe.get_all(
        "Wellbeing Record",
        filters={"owner": user},
        fields=["activity_type", "title", "impact_score", "logged_at"],
        order_by="logged_at desc",
        limit=10
    )

    return {
        "financial": financial_summary,
        "health": health_records,
        "wellbeing": wellbeing_records
    }