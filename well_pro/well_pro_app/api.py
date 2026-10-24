"""
WellPro REST API Endpoints
Provides authenticated CRUD, domain ingestion, daily score recalculation,
and historical multi-dimensional wellbeing dashboard endpoints.
"""
from typing import Optional, Dict, Any, Union
import frappe
from frappe import _
from frappe.utils import today, add_days

from well_pro.well_pro_app.services.scoring import (
    calculate_daily_score,
    get_user_dashboard
)

# -------------------------------------------------------------------
# SECURITY CONFIGURATION & ALLOWLISTS
# -------------------------------------------------------------------

ALLOWED_DOCTYPES = {
    "Health Daily Record",
    "Health Activity",
    "Financial Transaction",
    "Financial Snapshot",
    "Financial Category",
    "Social Activity",
    "Subjective Wellbeing Checkin",
    "User Consent Preference",
    "WellPro Profile",
    "Wellbeing Daily Score"
}

USER_OWNED_DOCTYPES = {
    "Health Daily Record",
    "Health Activity",
    "Financial Transaction",
    "Financial Snapshot",
    "Social Activity",
    "Subjective Wellbeing Checkin",
    "User Consent Preference",
    "WellPro Profile",
    "Wellbeing Daily Score"
}

PROTECTED_FIELDS = {
    "name", "owner", "creation", "modified_by", "docstatus", "idx"
}

DOMAIN_DOCTYPE_MAP = {
    "financial": "Financial Transaction",
    "health": "Health Daily Record",
    "health_activity": "Health Activity",
    "social": "Social Activity",
    "wellbeing": "Subjective Wellbeing Checkin"
}


def success_response(data: Any = None, message: str = "Success", **kwargs) -> Dict[str, Any]:
    """Generates standardized JSON success envelope."""
    res = {
        "success": True,
        "message": message,
        "data": data
    }
    res.update(kwargs)
    return res


def error_response(message: str = "An error occurred", errors: Optional[Dict[str, Any]] = None, code: int = 400) -> Dict[str, Any]:
    """Generates standardized JSON error envelope and sets HTTP status code."""
    frappe.response["http_status_code"] = code
    return {
        "success": False,
        "message": message,
        "errors": errors or {}
    }


def _validate_doctype(doctype: str) -> None:
    """Ensures requested DocType is strictly within WellPro's permitted allowlist."""
    if not doctype or doctype not in ALLOWED_DOCTYPES:
        frappe.throw(
            _("Access denied: DocType '{0}' is not permitted in WellPro API").format(doctype),
            frappe.PermissionError
        )


def _extract_affected_date(doc: Any) -> str:
    """Extracts the relevant YYYY-MM-DD date from a source record for score recalculation."""
    if hasattr(doc, "record_date") and doc.record_date:
        return str(doc.record_date)
    if hasattr(doc, "transaction_date") and doc.transaction_date:
        return str(doc.transaction_date)
    if hasattr(doc, "snapshot_date") and doc.snapshot_date:
        return str(doc.snapshot_date)
    if hasattr(doc, "date") and doc.date:
        return str(doc.date)
    if hasattr(doc, "score_date") and doc.score_date:
        return str(doc.score_date)
    if hasattr(doc, "logged_at") and doc.logged_at:
        return str(doc.logged_at).split()[0]
    return today()


# -------------------------------------------------------------------
# 1. USER AUTHENTICATION & REGISTRATION
# -------------------------------------------------------------------

@frappe.whitelist(allow_guest=True)
def signup(email: str, password: str, first_name: str, last_name: Optional[str] = None):
    """
    Registers a new standard WellPro user account, generates API credentials,
    and initializes their profile and consent preferences safely.
    Does NOT grant System Manager privileges to normal users.
    """
    if not email or "@" not in email:
        frappe.throw(_("A valid email address is required"), frappe.ValidationError)

    if not password or len(password) < 6:
        frappe.throw(_("Password must be at least 6 characters long"), frappe.ValidationError)

    if frappe.db.exists("User", email):
        frappe.throw(_("User with email {0} already exists").format(email), frappe.DuplicateEntryError)

    # Create standard user without System Manager role
    user = frappe.get_doc({
        "doctype": "User",
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "enabled": 1,
        "send_welcome_email": 0,
        "user_type": "System User"
    })
    user.insert(ignore_permissions=True)
    user.new_password = password
    user.save(ignore_permissions=True)

    # Generate API key & secret
    api_secret = frappe.generate_hash(length=15)
    api_key = frappe.generate_hash(length=15)
    user.api_key = api_key
    user.api_secret = api_secret
    user.save(ignore_permissions=True)

    # Auto-create WellPro Profile & Consent Preference if not existing
    if not frappe.db.exists("WellPro Profile", {"user": email}):
        frappe.get_doc({
            "doctype": "WellPro Profile",
            "user": email,
            "health_tracking_enabled": 1,
            "financial_tracking_enabled": 1,
            "social_tracking_enabled": 1
        }).insert(ignore_permissions=True)

    if not frappe.db.exists("User Consent Preference", {"user": email}):
        frappe.get_doc({
            "doctype": "User Consent Preference",
            "user": email,
            "health_tracking_enabled": 1,
            "financial_tracking_enabled": 1,
            "social_tracking_enabled": 1,
            "consent_version": "v1.0",
            "consent_updated_at": frappe.utils.now()
        }).insert(ignore_permissions=True)

    frappe.db.commit()

    return success_response(
        data={
            "user": email,
            "api_key": api_key,
            "api_secret": api_secret
        },
        message="User registered successfully"
    )


@frappe.whitelist(allow_guest=True)
def login(usr: str, pwd: str):
    """
    Authenticates user credentials and returns API key/secret pair.
    Generates API keys if they do not exist.
    """
    login_manager = frappe.auth.LoginManager()
    login_manager.authenticate(user=usr, pwd=pwd)
    login_manager.post_login()

    user = frappe.get_doc("User", usr)
    if not user.api_key or not user.api_secret:
        api_secret = frappe.generate_hash(length=15)
        api_key = frappe.generate_hash(length=15)
        user.api_key = api_key
        user.api_secret = api_secret
        user.save(ignore_permissions=True)
        frappe.db.commit()

    return success_response(
        data={
            "user": user.name,
            "api_key": user.api_key,
            "api_secret": user.get_password("api_secret")
        },
        message="Authentication successful"
    )


@frappe.whitelist()
def verify_user_session():
    """Verifies caller session token and returns active user profile and consent settings."""
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Unauthorized access: active session required"), frappe.AuthenticationError)

    profile = frappe.db.get_value("WellPro Profile", {"user": user}, "*", as_dict=True)
    consent = frappe.db.get_value("User Consent Preference", {"user": user}, "*", as_dict=True)
    return success_response(
        data={
            "user": user,
            "profile": profile,
            "consent": consent
        },
        message="Session valid"
    )


# -------------------------------------------------------------------
# 2. DATA INSERTION / CREATION APIs
# -------------------------------------------------------------------

@frappe.whitelist()
def insert_record(doctype: str, record_data: Any):
    """
    Generic insert endpoint enforcing strict DocType allowlist and user ownership.
    Authoritative identity: frappe.session.user always overrides any client value.
    Trigger score recalculation for the affected historical date.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Authentication required"), frappe.AuthenticationError)

    _validate_doctype(doctype)

    # Protect internal scores and master categories from unauthorized normal user insert
    if doctype == "Wellbeing Daily Score":
        frappe.throw(_("Daily scores are calculated by the scoring engine and cannot be inserted directly"), frappe.PermissionError)

    if doctype == "Financial Category" and "System Manager" not in frappe.get_roles(user):
        frappe.throw(_("Only System Managers can create Financial Categories"), frappe.PermissionError)

    if isinstance(record_data, str):
        record_data = frappe.parse_json(record_data)

    # DYNAMIC REFERENCE RESOLVER & AUTO-CREATION LAYER
    if doctype == "Financial Transaction" and record_data.get("category"):
        category_input = record_data["category"]
        
        # Check if the input value is NOT already a valid database primary key name
        if not frappe.db.exists("Financial Category", category_input):
            # Query the true name using the human-readable category_name field
            resolved_name = frappe.db.get_value("Financial Category", {"category_name": category_input}, "name")
            
            if resolved_name:
                record_data["category"] = resolved_name
            else:
                # Resolve transaction type to a valid category type options bound
                tx_type = record_data.get("transaction_type", "Expense")
                # Map select constraints: "Income", "Expense", "Investment", "Debt", "Transfer"
                category_type = tx_type if tx_type in ["Income", "Expense", "Investment", "Debt", "Transfer"] else "Expense"
                if tx_type == "Debt Payment":
                    category_type = "Debt"

                try:
                    # Dynamically instantiate the missing link record bypassing standard permissions
                    new_cat = frappe.get_doc({
                        "doctype": "Financial Category",
                        "category_name": category_input,
                        "category_type": category_type,
                        "active": 1,
                        "description": _("Auto-generated via dynamic ingestion pipeline")
                    })
                    new_cat.insert(ignore_permissions=True)
                    record_data["category"] = new_cat.name
                except Exception as e:
                    frappe.throw(
                        _("Failed to dynamically initialize Financial Category '{0}': {1}").format(category_input, str(e)),
                        frappe.LinkValidationError
                    )

    # DYNAMIC FIELD CLEANUP LAYER FOR OTHER DOCTYPES
    # Normalizes edge-case variant payload attributes from diverse client models or voice inputs
    if doctype == "Health Activity" and record_data.get("activity_type"):
        # Enforce validation against standard Select constraints: "Walking", "Running", "Cycling", "Gym", "Sports", "Other"
        if record_data["activity_type"] not in ["Walking", "Running", "Cycling", "Gym", "Sports", "Other"]:
            if not record_data.get("raw_input"):
                record_data["raw_input"] = f"Original Input: {record_data['activity_type']}"
            record_data["activity_type"] = "Other"

    if doctype == "Social Activity" and record_data.get("interaction_type"):
        # Enforce options alignment: "In Person", "Call", "Video Call", "Messaging", "Group Activity", "Community Activity", "Other"
        if record_data["interaction_type"] not in ["In Person", "Call", "Video Call", "Messaging", "Group Activity", "Community Activity", "Other"]:
            record_data["interaction_type"] = "Other"

    # Enforce authoritative ownership and remove protected system fields
    record_data["doctype"] = doctype
    if doctype in USER_OWNED_DOCTYPES:
        record_data["user"] = user

    for protected in PROTECTED_FIELDS:
        record_data.pop(protected, None)

    doc = frappe.get_doc(record_data)
    doc.insert(ignore_permissions=False)
    frappe.db.commit()

    # Recalculate score for the specific affected date (not blindly today)
    affected_date = _extract_affected_date(doc)
    try:
        calculate_daily_score(user, affected_date)
    except Exception as e:
        frappe.log_error(f"Score recalculation error on insert for {user}: {str(e)}", "WellPro Scoring Error")

    return success_response(
        data=doc.as_dict(),
        message=f"{doctype} created successfully"
    )



@frappe.whitelist()
def store_ai_record(domain: str, record_data: Any):
    """
    Dedicated endpoint used by FastAPI / AI extraction services to persist records.
    Enforces domain mapping, allowlists, and authoritative caller ownership.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Authentication required"), frappe.AuthenticationError)

    target_doctype = DOMAIN_DOCTYPE_MAP.get(domain)
    if not target_doctype:
        frappe.throw(
            _("Invalid target domain '{0}'. Allowed domains: {1}").format(domain, list(DOMAIN_DOCTYPE_MAP.keys())),
            frappe.ValidationError
        )

    if isinstance(record_data, str):
        record_data = frappe.parse_json(record_data)

    # 1. DYNAMIC REFERENCE RESOLVER & AUTO-CREATION LAYER (AI Engine Translation)
    if target_doctype == "Financial Transaction" and record_data.get("category"):
        category_input = record_data["category"]
        
        # Check if the AI-extracted category name is NOT already a valid database primary key
        if not frappe.db.exists("Financial Category", category_input):
            # Query the true name using the human-readable category_name field
            resolved_name = frappe.db.get_value("Financial Category", {"category_name": category_input}, "name")
            
            if resolved_name:
                record_data["category"] = resolved_name
            else:
                # Resolve transaction type to a valid category type options bound
                tx_type = record_data.get("transaction_type", "Expense")
                # Map select constraints: "Income", "Expense", "Investment", "Debt", "Transfer"
                category_type = tx_type if tx_type in ["Income", "Expense", "Investment", "Debt", "Transfer"] else "Expense"
                if tx_type == "Debt Payment":
                    category_type = "Debt"

                try:
                    # Dynamically instantiate the missing category record on the fly
                    new_cat = frappe.get_doc({
                        "doctype": "Financial Category",
                        "category_name": category_input,
                        "category_type": category_type,
                        "active": 1,
                        "description": _("Auto-generated via AI Data Ingestion pipeline")
                    })
                    new_cat.insert(ignore_permissions=True)
                    record_data["category"] = new_cat.name
                except Exception as e:
                    frappe.throw(
                        _("AI Ingestion failed to dynamically initialize Financial Category '{0}': {1}").format(category_input, str(e)),
                        frappe.LinkValidationError
                    )

    # 2. DYNAMIC FIELD CLEANUP LAYER FOR OTHER DOMAINS (AI Out-of-bounds Normalization)
    if target_doctype == "Health Activity" and record_data.get("activity_type"):
        # Enforce validation against standard Select constraints: "Walking", "Running", "Cycling", "Gym", "Sports", "Other"
        if record_data["activity_type"] not in ["Walking", "Running", "Cycling", "Gym", "Sports", "Other"]:
            if not record_data.get("raw_input"):
                record_data["raw_input"] = f"Original AI Output: {record_data['activity_type']}"
            record_data["activity_type"] = "Other"

    if target_doctype == "Social Activity" and record_data.get("interaction_type"):
        # Enforce options alignment: "In Person", "Call", "Video Call", "Messaging", "Group Activity", "Community Activity", "Other"
        if record_data["interaction_type"] not in ["In Person", "Call", "Video Call", "Messaging", "Group Activity", "Community Activity", "Other"]:
            record_data["interaction_type"] = "Other"

    # Enforce authoritative ownership and remove protected system fields
    record_data["doctype"] = target_doctype
    record_data["user"] = user

    for protected in PROTECTED_FIELDS:
        record_data.pop(protected, None)

    doc = frappe.get_doc(record_data)
    doc.insert(ignore_permissions=False)
    frappe.db.commit()

    # Recalculate score for the specific date of the record
    affected_date = _extract_affected_date(doc)
    try:
        calculate_daily_score(user, affected_date)
    except Exception as e:
        frappe.log_error(f"Score recalculation error on AI store for {user}: {str(e)}", "WellPro Scoring Error")

    return success_response(
        data=doc.as_dict(),
        message=f"Saved to {target_doctype}"
    )



# -------------------------------------------------------------------
# 3. DATA UPDATE APIs
# -------------------------------------------------------------------

@frappe.whitelist()
def update_record(doctype: str, name: str, update_data: Any):
    """
    Safely updates an existing user record.
    Enforces allowlist, ownership isolation, and prevents mass assignment of protected fields.
    Recalculates scores for affected dates.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Authentication required"), frappe.AuthenticationError)

    _validate_doctype(doctype)

    if doctype == "Wellbeing Daily Score":
        frappe.throw(_("Daily scores cannot be manually edited"), frappe.PermissionError)

    if not frappe.db.exists(doctype, name):
        frappe.throw(_("Record {0} of type {1} not found").format(name, doctype), frappe.DoesNotExistError)

    doc = frappe.get_doc(doctype, name)

    # Ownership check: Normal users can only update their own records
    is_admin = "System Manager" in frappe.get_roles(user)
    if doctype in USER_OWNED_DOCTYPES:
        if getattr(doc, "user", None) != user and not is_admin:
            frappe.throw(_("Permission denied: You do not own this record"), frappe.PermissionError)
    elif not is_admin:
        frappe.throw(_("Permission denied: Only administrators can modify this record"), frappe.PermissionError)

    if isinstance(update_data, str):
        update_data = frappe.parse_json(update_data)

    # 1. DYNAMIC REFERENCE RESOLVER & AUTO-CREATION LAYER (On Update)
    if doctype == "Financial Transaction" and update_data.get("category"):
        category_input = update_data["category"]
        
        # Check if the updated input value is NOT already a valid database primary key name
        if not frappe.db.exists("Financial Category", category_input):
            # Query the true name using the human-readable category_name field
            resolved_name = frappe.db.get_value("Financial Category", {"category_name": category_input}, "name")
            
            if resolved_name:
                update_data["category"] = resolved_name
            else:
                # Fallback to current transaction type if type isn't changing in update_data
                tx_type = update_data.get("transaction_type") or getattr(doc, "transaction_type", "Expense")
                # Map select constraints: "Income", "Expense", "Investment", "Debt", "Transfer"
                category_type = tx_type if tx_type in ["Income", "Expense", "Investment", "Debt", "Transfer"] else "Expense"
                if tx_type == "Debt Payment":
                    category_type = "Debt"

                try:
                    # Dynamically instantiate the missing link record bypassing standard permissions
                    new_cat = frappe.get_doc({
                        "doctype": "Financial Category",
                        "category_name": category_input,
                        "category_type": category_type,
                        "active": 1,
                        "description": _("Auto-generated via dynamic update pipeline")
                    })
                    new_cat.insert(ignore_permissions=True)
                    update_data["category"] = new_cat.name
                except Exception as e:
                    frappe.throw(
                        _("Failed to dynamically initialize Financial Category '{0}' on update: {1}").format(category_input, str(e)),
                        frappe.LinkValidationError
                    )

    # 2. DYNAMIC FIELD CLEANUP LAYER FOR OTHER DOCTYPES (On Update)
    if doctype == "Health Activity" and update_data.get("activity_type"):
        if update_data["activity_type"] not in ["Walking", "Running", "Cycling", "Gym", "Sports", "Other"]:
            if not update_data.get("raw_input"):
                update_data["raw_input"] = f"Updated Input Variance: {update_data['activity_type']}"
            update_data["activity_type"] = "Other"

    if doctype == "Social Activity" and update_data.get("interaction_type"):
        if update_data["interaction_type"] not in ["In Person", "Call", "Video Call", "Messaging", "Group Activity", "Community Activity", "Other"]:
            update_data["interaction_type"] = "Other"

    # Prevent tampering with ownership, identity, or protected fields
    for forbidden in PROTECTED_FIELDS | {"user", "doctype"}:
        update_data.pop(forbidden, None)

    old_date = _extract_affected_date(doc)
    doc.update(update_data)
    doc.save(ignore_permissions=False)
    frappe.db.commit()

    # Recalculate scores for old date and new date if date was modified
    new_date = _extract_affected_date(doc)
    target_user = doc.user if hasattr(doc, "user") else user
    try:
        calculate_daily_score(target_user, old_date)
        if new_date != old_date:
            calculate_daily_score(target_user, new_date)
    except Exception as e:
        frappe.log_error(f"Score recalculation error on update for {target_user}: {str(e)}", "WellPro Scoring Error")

    return success_response(
        data=doc.as_dict(),
        message=f"{doctype} updated successfully"
    )



# -------------------------------------------------------------------
# 4. DATA DELETION APIs
# -------------------------------------------------------------------

@frappe.whitelist()
def delete_record(doctype: str, name: str):
    """
    Safely deletes a record owned by the authenticated user.
    Recalculates the affected day's wellbeing score automatically.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Authentication required"), frappe.AuthenticationError)

    _validate_doctype(doctype)

    # 1. CORE PERMISSION AND PROTECTION LAYER
    if doctype == "Wellbeing Daily Score":
        frappe.throw(_("Daily scores cannot be directly deleted"), frappe.PermissionError)

    # Protect Master Configuration items from accidental API purge by standard users
    if doctype == "Financial Category":
        if "System Manager" not in frappe.get_roles(user):
            frappe.throw(_("Permission denied: System master data configurations cannot be deleted via general user endpoint"), frappe.PermissionError)
        # Prevent deletion if active financial ledger transactions are still linked to this category
        if frappe.db.exists("Financial Transaction", {"category": name}):
            frappe.throw(_("Cannot delete Financial Category '{0}' because active transactions are linked to it. Purge transactions first.").format(name), frappe.LinkValidationError)

    if not frappe.db.exists(doctype, name):
        frappe.throw(_("Record {0} of type {1} not found").format(name, doctype), frappe.DoesNotExistError)

    # 2. STATE EXTRACTION (Prior to deletion execution)
    doc = frappe.get_doc(doctype, name)

    is_admin = "System Manager" in frappe.get_roles(user)
    if doctype in USER_OWNED_DOCTYPES:
        if getattr(doc, "user", None) != user and not is_admin:
            frappe.throw(_("Permission denied: You do not own this record"), frappe.PermissionError)
    elif not is_admin:
        frappe.throw(_("Permission denied: Only administrators can delete this record"), frappe.PermissionError)

    # Cache target user and date parameters safely into memory variables before document eviction
    affected_date = _extract_affected_date(doc)
    target_user = doc.user if hasattr(doc, "user") else user

    # 3. SECURE EVICTION AND SCORE RE-CALCULATION
    frappe.delete_doc(doctype, name, ignore_permissions=False, force=False)
    frappe.db.commit()

    # Refresh score matrix state safely after commit pipeline finishes execution
    try:
        calculate_daily_score(target_user, affected_date)
    except Exception as e:
        frappe.log_error(f"Score recalculation error on delete for {target_user}: {str(e)}", "WellPro Scoring Error")

    return success_response(
        data={"doctype": doctype, "name": name},
        message=f"{doctype} deleted successfully"
    )



# -------------------------------------------------------------------
# 5. DATA RETRIEVAL APIs
# -------------------------------------------------------------------

@frappe.whitelist()
def get_user_records(
    doctype: str,
    limit: str = 50,
    offset: str = 0,
    order_by: str = "modified desc",
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
):
    """
    Retrieves records for the logged-in user with safe pagination and date filtering.
    Enforces allowlist and user isolation strictly.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Authentication required"), frappe.AuthenticationError)

    _validate_doctype(doctype)

    filters = {}
    if doctype in USER_OWNED_DOCTYPES:
        filters["user"] = user

    # Apply date filters to the primary date field of the doctype if provided
    date_field_map = {
        "Health Daily Record": "record_date",
        "Financial Transaction": "transaction_date",
        "Financial Snapshot": "snapshot_date",
        "Subjective Wellbeing Checkin": "date",
        "Wellbeing Daily Score": "score_date",
        "Health Activity": "logged_at",
        "Social Activity": "logged_at"
    }

    date_field = date_field_map.get(doctype)
    if date_field and (from_date or to_date):
        if from_date and to_date:
            filters[date_field] = ["between", [from_date, to_date]]
        elif from_date:
            filters[date_field] = [">=", from_date]
        elif to_date:
            filters[date_field] = ["<=", to_date]

    records = frappe.get_all(
        doctype,
        filters=filters,
        fields=["*"],
        order_by=order_by,
        limit_start=int(offset),
        limit_page_length=min(int(limit), 200)
    )

    return success_response(
        data=records,
        count=len(records),
        limit=int(limit),
        offset=int(offset)
    )


# -------------------------------------------------------------------
# 6. SCORING & DASHBOARD APIs
# -------------------------------------------------------------------

@frappe.whitelist(methods=["POST"])
def recalculate_score(date: Optional[str] = None, target_user: Optional[str] = None):
    """
    Triggers explicit recalculation of a user's daily score for a given date.
    Authenticated caller's identity is strictly authoritative unless caller is System Manager.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Authentication required"), frappe.AuthenticationError)

    # Protect user isolation: only System Manager can calculate another user's score
    effective_user = user
    if target_user and target_user != user:
        if "System Manager" not in frappe.get_roles(user):
            frappe.throw(_("Permission denied: Cannot recalculate score for another user"), frappe.PermissionError)
        effective_user = target_user

    calc_date = date or today()
    result = calculate_daily_score(effective_user, calc_date)

    return success_response(
        data=result,
        message=f"Wellbeing score for {calc_date} calculated successfully"
    )


@frappe.whitelist(methods=["GET"])
def get_dashboard(as_of_date: Optional[str] = None):
    """
    Returns full multi-dimensional Wellbeing Dashboard data for the authenticated user.
    Includes today score, 30-day exponential recency-weighted score, 7-day, 90-day scores,
    confidences, and trends for Health, Financial, Social, and Overall wellbeing.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Authentication required"), frappe.AuthenticationError)

    dashboard_data = get_user_dashboard(user, as_of_date or today())
    return success_response(
        data=dashboard_data,
        message="Dashboard metrics retrieved successfully"
    )


@frappe.whitelist(methods=["GET"])
def get_dashboard_metrics(days: int = 30):
    """
    Backward-compatibility endpoint for legacy dashboard consumers.
    Returns modern scoring metrics together with raw activity feeds.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Authentication required"), frappe.AuthenticationError)

    start_date = add_days(today(), -int(days))

    # Fetch daily scores
    scores = frappe.get_all(
        "Wellbeing Daily Score",
        filters={"user": user, "score_date": [">=", start_date]},
        fields=[
            "score_date", "health_score", "health_confidence",
            "financial_score", "financial_confidence",
            "social_score", "social_confidence", "overall_score"
        ],
        order_by="score_date asc"
    )

    # Refresh current score
    latest_score = calculate_daily_score(user, today())

    # Raw Recent Records
    financial = frappe.get_all("Financial Transaction", filters={"user": user}, fields=["*"], order_by="transaction_date desc", limit=10)
    health = frappe.get_all("Health Daily Record", filters={"user": user}, fields=["*"], order_by="record_date desc", limit=10)
    social = frappe.get_all("Social Activity", filters={"user": user}, fields=["*"], order_by="logged_at desc", limit=10)

    return success_response(
        data={
            "current_scores": latest_score,
            "historical_trends": scores,
            "financial": financial,
            "health": health,
            "social": social
        },
        message="Metrics retrieved"
    )
