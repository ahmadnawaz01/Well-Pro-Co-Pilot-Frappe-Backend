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
    get_user_dashboard,
    get_user_scoring_config,
    get_user_custom_goals,
    parse_custom_goals,
    convert_goal_to_config_scale,
    DEFAULT_SCORING_CONFIG
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


DOCTYPE_ALIASES = {
    # Official names
    "health daily record": "Health Daily Record",
    "health activity": "Health Activity",
    "financial transaction": "Financial Transaction",
    "financial snapshot": "Financial Snapshot",
    "financial category": "Financial Category",
    "social activity": "Social Activity",
    "subjective wellbeing checkin": "Subjective Wellbeing Checkin",
    "user consent preference": "User Consent Preference",
    "wellpro profile": "WellPro Profile",
    "wellbeing daily score": "Wellbeing Daily Score",

    # Underscore / snake_case names
    "health_daily_record": "Health Daily Record",
    "health_activity": "Health Activity",
    "financial_transaction": "Financial Transaction",
    "financial_snapshot": "Financial Snapshot",
    "financial_category": "Financial Category",
    "social_activity": "Social Activity",
    "subjective_wellbeing_checkin": "Subjective Wellbeing Checkin",
    "user_consent_preference": "User Consent Preference",
    "wellpro_profile": "WellPro Profile",
    "wellbeing_daily_score": "Wellbeing Daily Score",

    # Domain aliases
    "health": "Health Daily Record",
    "activity": "Health Activity",
    "exercise": "Health Activity",
    "financial": "Financial Transaction",
    "finance": "Financial Transaction",
    "transaction": "Financial Transaction",
    "transactions": "Financial Transaction",
    "snapshot": "Financial Snapshot",
    "social": "Social Activity",
    "checkin": "Subjective Wellbeing Checkin",
    "wellbeing": "Subjective Wellbeing Checkin",
    "profile": "WellPro Profile",
    "consent": "User Consent Preference"
}


def _resolve_doctype_name(identifier: Optional[str]) -> Optional[str]:
    """Resolves an identifier (name, snake_case, or domain alias) to a valid WellPro DocType name."""
    if not identifier:
        return None
    ident_str = str(identifier).strip()
    if ident_str in ALLOWED_DOCTYPES:
        return ident_str
    lower_norm = ident_str.lower().replace("-", "_").replace(" ", "_")
    if lower_norm in DOCTYPE_ALIASES:
        return DOCTYPE_ALIASES[lower_norm]
    spaced = ident_str.lower().replace("_", " ")
    if spaced in DOCTYPE_ALIASES:
        return DOCTYPE_ALIASES[spaced]
    return None


def _extract_affected_date(doc: Any) -> str:
    """Extracts the relevant YYYY-MM-DD date from a source record or dict for score recalculation."""
    def _get(field):
        if isinstance(doc, dict):
            return doc.get(field)
        return getattr(doc, field, None)

    for field in ("record_date", "transaction_date", "snapshot_date", "date", "score_date"):
        val = _get(field)
        if val:
            return str(val)

    logged = _get("logged_at")
    if logged:
        return str(logged).split()[0]

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
# 2. DATA INSERTION / CREATION APIs (SINGLE, BATCH & MULTI-DOCTYPE)
# -------------------------------------------------------------------


def _upsert_accumulate_daily_record(doctype: str, record_data: dict, user: str) -> Optional[Any]:
    """
    If a record with a unique constraint (Health Daily Record, Financial Snapshot,
    Subjective Wellbeing Checkin, WellPro Profile, User Consent Preference) already exists
    for this user on the given date, accumulates or updates the existing record instead of
    failing with DuplicateEntryError. Returns the updated document, or None.
    """
    if doctype == "Health Daily Record":
        rec_date = record_data.get("record_date") or today()
        existing = frappe.db.exists("Health Daily Record", {"user": user, "record_date": rec_date})
        if existing:
            doc = frappe.get_doc("Health Daily Record", existing)
            doc.steps = (doc.steps or 0) + int(record_data.get("steps") or 0)
            doc.exercise_minutes = (doc.exercise_minutes or 0) + int(record_data.get("exercise_minutes") or 0)
            doc.active_minutes = (doc.active_minutes or 0) + int(record_data.get("active_minutes") or 0)
            if "water_liters" in record_data and record_data["water_liters"] is not None:
                doc.water_liters = round((doc.water_liters or 0.0) + float(record_data["water_liters"]), 2)
            if "calories_consumed" in record_data and record_data["calories_consumed"] is not None:
                doc.calories_consumed = round((doc.calories_consumed or 0.0) + float(record_data["calories_consumed"]), 1)
            if "protein_grams" in record_data and record_data["protein_grams"] is not None:
                doc.protein_grams = round((doc.protein_grams or 0.0) + float(record_data["protein_grams"]), 1)
            if "fruit_veg_servings" in record_data and record_data["fruit_veg_servings"] is not None:
                doc.fruit_veg_servings = round((doc.fruit_veg_servings or 0.0) + float(record_data["fruit_veg_servings"]), 1)

            for fld in ["sleep_hours", "sleep_quality", "energy_level", "self_rated_health", "exercise_intensity", "source"]:
                if fld in record_data and record_data[fld] is not None:
                    setattr(doc, fld, record_data[fld])

            doc.save(ignore_permissions=True)
            frappe.db.commit()
            return doc

    elif doctype == "Financial Snapshot":
        snap_date = record_data.get("snapshot_date") or today()
        existing = frappe.db.exists("Financial Snapshot", {"user": user, "snapshot_date": snap_date})
        if existing:
            doc = frappe.get_doc("Financial Snapshot", existing)
            for fld, val in record_data.items():
                if fld not in PROTECTED_FIELDS and fld not in ["doctype", "user", "name"]:
                    setattr(doc, fld, val)
            doc.save(ignore_permissions=True)
            frappe.db.commit()
            return doc

    elif doctype == "Subjective Wellbeing Checkin":
        chk_date = record_data.get("date") or today()
        existing = frappe.db.exists("Subjective Wellbeing Checkin", {"user": user, "date": chk_date})
        if existing:
            doc = frappe.get_doc("Subjective Wellbeing Checkin", existing)
            for fld in ["mood", "energy", "stress", "social_connection", "loneliness", "social_satisfaction", "financial_stress"]:
                if fld in record_data and record_data[fld] is not None:
                    setattr(doc, fld, int(record_data[fld]))
            doc.save(ignore_permissions=True)
            frappe.db.commit()
            return doc

    elif doctype == "User Consent Preference":
        existing = frappe.db.exists("User Consent Preference", {"user": user})
        if existing:
            doc = frappe.get_doc("User Consent Preference", existing)
            for fld, val in record_data.items():
                if fld not in PROTECTED_FIELDS and fld not in ["doctype", "user", "name"]:
                    setattr(doc, fld, val)
            doc.save(ignore_permissions=True)
            frappe.db.commit()
            return doc

    elif doctype == "WellPro Profile":
        existing = frappe.db.exists("WellPro Profile", {"user": user})
        if existing:
            doc = frappe.get_doc("WellPro Profile", existing)
            for fld, val in record_data.items():
                if fld not in PROTECTED_FIELDS and fld not in ["doctype", "user", "name"]:
                    setattr(doc, fld, val)
            doc.save(ignore_permissions=True)
            frappe.db.commit()
            return doc

    return None


def _process_single_insert(doctype: str, record_data: Any, user: str) -> Tuple[Any, str]:
    """Internal helper to validate, normalize, and insert/upsert a single record."""
    if not doctype:
        frappe.throw(_("Missing 'doctype' in record specification"), frappe.MandatoryError)

    resolved_dt = _resolve_doctype_name(doctype)
    if not resolved_dt:
        _validate_doctype(doctype)
    doctype = resolved_dt

    _validate_doctype(doctype)

    if doctype == "Wellbeing Daily Score":
        frappe.throw(_("Daily scores are calculated by the scoring engine and cannot be inserted directly"), frappe.PermissionError)

    if doctype == "Financial Category" and "System Manager" not in frappe.get_roles(user):
        frappe.throw(_("Only System Managers can create Financial Categories"), frappe.PermissionError)

    if isinstance(record_data, str):
        record_data = frappe.parse_json(record_data)
    elif not isinstance(record_data, dict):
        frappe.throw(_("record_data must be a valid JSON object or dict"), frappe.ValidationError)

    # Clone dict to prevent mutation side-effects
    record_data = dict(record_data)

    # Fill default required dates/times if omitted
    if doctype == "Health Daily Record" and not record_data.get("record_date"):
        record_data["record_date"] = today()
    elif doctype == "Financial Transaction" and not record_data.get("transaction_date"):
        record_data["transaction_date"] = today()
    elif doctype == "Financial Snapshot" and not record_data.get("snapshot_date"):
        record_data["snapshot_date"] = today()
    elif doctype == "Subjective Wellbeing Checkin" and not record_data.get("date"):
        record_data["date"] = today()
    elif doctype in ("Health Activity", "Social Activity") and not record_data.get("logged_at"):
        record_data["logged_at"] = frappe.utils.now()

    # 1. Rating Boundary Validation (1 to 5)
    rating_fields = {
        "Health Daily Record": {"sleep_quality", "energy_level", "self_rated_health"},
        "Financial Snapshot": {"financial_stress_rating"},
        "Social Activity": {"interaction_quality", "connection_level", "mood_after"},
        "Subjective Wellbeing Checkin": {"mood", "energy", "stress", "social_connection", "loneliness", "social_satisfaction", "financial_stress"}
    }
    if doctype in rating_fields:
        for rf in rating_fields[doctype]:
            if rf in record_data and record_data[rf] is not None:
                val = int(record_data[rf])
                if val < 1 or val > 5:
                    frappe.throw(_("Field '{0}' in '{1}' must be an integer between 1 and 5").format(rf, doctype), frappe.ValidationError)
                record_data[rf] = val

    # 2. Financial Transaction Checks & Auto-Defaults
    if doctype == "Financial Transaction":
        if "amount" in record_data and record_data["amount"] is not None:
            if float(record_data["amount"]) <= 0:
                frappe.throw(_("Transaction amount must be strictly greater than 0"), frappe.ValidationError)
        else:
            frappe.throw(_("Transaction amount is required"), frappe.MandatoryError)

        tx_type = record_data.get("transaction_type") or "Expense"
        if tx_type not in ["Income", "Expense", "Transfer", "Investment", "Debt Payment"]:
            tx_type = "Expense"
        record_data["transaction_type"] = tx_type

        # Dynamic Category Resolver
        category_input = str(record_data.get("category") or "General").strip()
        if not frappe.db.exists("Financial Category", category_input):
            resolved_name = frappe.db.get_value("Financial Category", {"category_name": category_input}, "name")
            if resolved_name:
                record_data["category"] = resolved_name
            else:
                category_type = tx_type if tx_type in ["Income", "Expense", "Investment", "Debt", "Transfer"] else "Expense"
                if tx_type == "Debt Payment":
                    category_type = "Debt"

                try:
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

    # 3. Standard Options Normalization
    if doctype == "Health Activity":
        act_type = record_data.get("activity_type") or "Other"
        if act_type not in ["Walking", "Running", "Cycling", "Gym", "Sports", "Other"]:
            if not record_data.get("raw_input"):
                record_data["raw_input"] = f"Original Input: {act_type}"
            act_type = "Other"
        record_data["activity_type"] = act_type

    if doctype == "Social Activity":
        int_type = record_data.get("interaction_type") or "Other"
        if int_type not in ["In Person", "Call", "Video Call", "Messaging", "Group Activity", "Community Activity", "Other"]:
            int_type = "Other"
        record_data["interaction_type"] = int_type

        rel_type = record_data.get("relationship_type") or "Other"
        if rel_type not in ["Family", "Friend", "Partner", "Colleague", "Community", "Other"]:
            rel_type = "Other"
        record_data["relationship_type"] = rel_type

    # 4. Authoritative Identity & Strip Prohibited System Fields
    record_data["doctype"] = doctype
    if doctype in USER_OWNED_DOCTYPES:
        record_data["user"] = user

    for protected in PROTECTED_FIELDS:
        record_data.pop(protected, None)

    # 5. Execute Upsert or Insert
    existing_doc = _upsert_accumulate_daily_record(doctype, record_data, user)
    if existing_doc:
        doc = existing_doc
    else:
        doc = frappe.get_doc(record_data)
        doc.insert(ignore_permissions=False)

    affected_date = _extract_affected_date(doc)
    return doc, affected_date


def _normalize_batch_payload(
    doctype: Optional[str] = None,
    record_data: Optional[Any] = None,
    records: Optional[Any] = None,
    domain: Optional[str] = None,
    raw_body_or_kwargs: Optional[Dict[str, Any]] = None,
    default_source: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Normalizes single, batch, multi-doctype, or domain payloads into a uniform list:
    [
        {"doctype": "DocType Name", "record_data": {...}},
        ...
    ]
    Returns (normalized_records, is_single).
    """
    raw_dict = {}
    if isinstance(raw_body_or_kwargs, dict):
        raw_dict.update(raw_body_or_kwargs)

    # 1. Direct list passed as records
    if isinstance(records, str):
        try:
            records = frappe.parse_json(records)
        except Exception:
            pass

    if isinstance(records, list):
        items = []
        for idx, item in enumerate(records):
            if isinstance(item, str):
                item = frappe.parse_json(item)
            if not isinstance(item, dict):
                frappe.throw(_("Record at index {0} must be a dictionary").format(idx), frappe.ValidationError)

            item_dt = item.get("doctype") or item.get("domain") or doctype or domain
            resolved_dt = _resolve_doctype_name(item_dt)
            if not resolved_dt:
                frappe.throw(_("Unknown or missing DocType/domain in record at index {0}").format(idx), frappe.ValidationError)

            if "record_data" in item and isinstance(item["record_data"], (dict, str)):
                sub_data = item["record_data"]
                if isinstance(sub_data, str):
                    sub_data = frappe.parse_json(sub_data)
                d = dict(sub_data)
            else:
                d = {k: v for k, v in item.items() if k not in ("doctype", "domain", "index")}

            if default_source and not d.get("source"):
                d["source"] = default_source

            items.append({"doctype": resolved_dt, "record_data": d})
        return items, False

    # 2. Multi-DocType / Multi-Domain Dictionary on Single Request
    # e.g. {"Health Daily Record": {...}, "Financial Transaction": [{...}], "social": {...}}
    dt_keys = [
        k for k in raw_dict.keys()
        if _resolve_doctype_name(k) is not None and k not in ("doctype", "domain", "cmd", "atomic", "record_data", "records")
    ]
    if dt_keys:
        items = []
        for k in dt_keys:
            resolved_dt = _resolve_doctype_name(k)
            val = raw_dict[k]
            if isinstance(val, str):
                try:
                    val = frappe.parse_json(val)
                except Exception:
                    pass

            if isinstance(val, list):
                for sub in val:
                    if isinstance(sub, str):
                        sub = frappe.parse_json(sub)
                    if isinstance(sub, dict):
                        d = dict(sub)
                        if default_source and not d.get("source"):
                            d["source"] = default_source
                        items.append({"doctype": resolved_dt, "record_data": d})
            elif isinstance(val, dict):
                d = dict(val)
                if default_source and not d.get("source"):
                    d["source"] = default_source
                items.append({"doctype": resolved_dt, "record_data": d})

        if items:
            return items, len(items) == 1

    # 3. Single record format
    eff_identifier = doctype or domain or raw_dict.get("doctype") or raw_dict.get("domain")
    eff_dt = _resolve_doctype_name(eff_identifier)
    if eff_dt:
        if record_data is not None:
            if isinstance(record_data, str):
                record_data = frappe.parse_json(record_data)
            d = dict(record_data) if isinstance(record_data, dict) else {}
        elif "record_data" in raw_dict:
            rd = raw_dict["record_data"]
            if isinstance(rd, str):
                rd = frappe.parse_json(rd)
            d = dict(rd) if isinstance(rd, dict) else {}
        else:
            d = {k: v for k, v in raw_dict.items() if k not in ("doctype", "domain", "cmd", "atomic", "record_data", "records")}

        if default_source and not d.get("source"):
            d["source"] = default_source

        return [{"doctype": eff_dt, "record_data": d}], True

    return [], False


@frappe.whitelist(methods=["GET", "POST"])
def insert_record(
    doctype: Optional[str] = None,
    record_data: Optional[Any] = None,
    records: Optional[Any] = None,
    atomic: Any = True,
    **kwargs
):
    """
    Universal Ingestion API:
    Supports:
    1. Single record:
       - Pass `doctype` and `record_data`
       - OR pass `doctype` and flat fields (e.g. `{"doctype": "Health Daily Record", "steps": 8000}`)
    2. Batch records:
       - Pass `records` as a list of dicts (flat or nested `record_data`)
       - OR pass a JSON array as root request payload
    3. Multi-DocType on a single request:
       - Pass multiple DocTypes in a single object:
         {
             "Health Daily Record": {"steps": 8000, "sleep_hours": 7.5},
             "Financial Transaction": [{"amount": 25, "category": "Food"}],
             "Social Activity": {"activity_name": "Lunch"}
         }
    Automatically recalculates wellbeing scores for all affected dates immediately after insertion.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Authentication required"), frappe.AuthenticationError)

    req_body = None
    try:
        req_body = frappe.request.get_json() if hasattr(frappe, "request") and frappe.request else None
    except Exception:
        pass

    combined_raw = {}
    if isinstance(req_body, dict):
        combined_raw.update(req_body)
    if kwargs:
        combined_raw.update(kwargs)

    is_atomic = atomic in (True, 1, "1", "true", "True")
    if "atomic" in combined_raw:
        is_atomic = combined_raw["atomic"] in (True, 1, "1", "true", "True")

    effective_records = records or (req_body if isinstance(req_body, list) else None)
    normalized_records, is_single = _normalize_batch_payload(
        doctype=doctype,
        record_data=record_data,
        records=effective_records,
        raw_body_or_kwargs=combined_raw
    )

    if not normalized_records:
        frappe.throw(
            _("No valid record data provided. Provide either 'records' list, a multi-doctype dictionary, or 'doctype' and 'record_data'."),
            frappe.MandatoryError
        )

    created_records = []
    errors = []
    affected_dates = set()

    if is_atomic:
        for idx, item in enumerate(normalized_records):
            doc, aff_dt = _process_single_insert(
                doctype=item["doctype"],
                record_data=item["record_data"],
                user=user
            )
            affected_dates.add(aff_dt)
            created_records.append({
                "index": idx,
                "doctype": item["doctype"],
                "name": doc.name,
                "affected_date": aff_dt,
                "record": doc.as_dict()
            })

        frappe.db.commit()

        # Recalculate score for all touched dates
        recalc_scores = {}
        for dt in affected_dates:
            try:
                recalc_scores[dt] = calculate_daily_score(user, dt)
            except Exception as e:
                frappe.log_error(f"Score recalculation error for {user} on {dt}: {str(e)}", "WellPro Scoring Error")

        if is_single and len(created_records) == 1:
            first = created_records[0]
            return success_response(
                data=first["record"],
                name=first["name"],
                doctype=first["doctype"],
                affected_date=first["affected_date"],
                recalculated_score=recalc_scores.get(first["affected_date"]),
                message=f"{first['doctype']} created successfully"
            )

        return success_response(
            data={
                "created": created_records,
                "count": len(created_records),
                "affected_dates": sorted(list(affected_dates)),
                "recalculated_scores": recalc_scores
            },
            message=f"Successfully created {len(created_records)} records"
        )
    else:
        for idx, item in enumerate(normalized_records):
            sp_name = f"batch_sp_{idx}"
            frappe.db.savepoint(sp_name)
            try:
                doc, aff_dt = _process_single_insert(
                    doctype=item["doctype"],
                    record_data=item["record_data"],
                    user=user
                )
                affected_dates.add(aff_dt)
                created_records.append({
                    "index": idx,
                    "doctype": item["doctype"],
                    "name": doc.name,
                    "affected_date": aff_dt,
                    "record": doc.as_dict()
                })
            except Exception as ex:
                frappe.db.rollback(save_point=sp_name)
                errors.append({
                    "index": idx,
                    "doctype": item.get("doctype"),
                    "error": str(ex)
                })

        frappe.db.commit()

        recalc_scores = {}
        for dt in affected_dates:
            try:
                recalc_scores[dt] = calculate_daily_score(user, dt)
            except Exception as e:
                frappe.log_error(f"Score recalculation error for {user} on {dt}: {str(e)}", "WellPro Scoring Error")

        return success_response(
            data={
                "created": created_records,
                "errors": errors,
                "successful_count": len(created_records),
                "failed_count": len(errors),
                "affected_dates": sorted(list(affected_dates)),
                "recalculated_scores": recalc_scores
            },
            message=f"Batch processed: {len(created_records)} succeeded, {len(errors)} failed"
        )


@frappe.whitelist(methods=["GET", "POST"])
def store_ai_record(
    domain: Optional[str] = None,
    record_data: Optional[Any] = None,
    records: Optional[Any] = None,
    doctype: Optional[str] = None,
    atomic: Any = True,
    **kwargs
):
    """
    Dedicated AI Extraction Ingestion API:
    Supports:
    1. Single Extraction: Pass `domain` (or `doctype`) and `record_data` (or flat fields)
    2. Batch Extractions: Pass `records` list of domain extractions
    3. Multi-Domain Payload:
       {
           "health": {"steps": 8000, "sleep_hours": 7},
           "financial": [{"amount": 45, "category": "Groceries"}],
           "social": {"activity_name": "Dinner with friends"}
       }
    Automatically assigns source='AI Extraction' and recalculates daily scores for all affected dates.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Authentication required"), frappe.AuthenticationError)

    req_body = None
    try:
        req_body = frappe.request.get_json() if hasattr(frappe, "request") and frappe.request else None
    except Exception:
        pass

    combined_raw = {}
    if isinstance(req_body, dict):
        combined_raw.update(req_body)
    if kwargs:
        combined_raw.update(kwargs)

    is_atomic = atomic in (True, 1, "1", "true", "True")
    if "atomic" in combined_raw:
        is_atomic = combined_raw["atomic"] in (True, 1, "1", "true", "True")

    effective_records = records or (req_body if isinstance(req_body, list) else None)
    normalized_records, is_single = _normalize_batch_payload(
        doctype=doctype,
        record_data=record_data,
        records=effective_records,
        domain=domain,
        raw_body_or_kwargs=combined_raw,
        default_source="AI Extraction"
    )

    if not normalized_records:
        frappe.throw(
            _("No valid AI record extractions found to store. Provide 'domain'/'doctype' and record data, a multi-domain dictionary, or 'records' list."),
            frappe.MandatoryError
        )

    created_records = []
    errors = []
    affected_dates = set()

    if is_atomic:
        for idx, item in enumerate(normalized_records):
            doc, aff_dt = _process_single_insert(
                doctype=item["doctype"],
                record_data=item["record_data"],
                user=user
            )
            affected_dates.add(aff_dt)
            created_records.append({
                "index": idx,
                "doctype": item["doctype"],
                "name": doc.name,
                "affected_date": aff_dt,
                "record": doc.as_dict()
            })

        frappe.db.commit()

        recalc_scores = {}
        for dt in affected_dates:
            try:
                recalc_scores[dt] = calculate_daily_score(user, dt)
            except Exception as e:
                frappe.log_error(f"Score recalculation error for {user} on {dt}: {str(e)}", "WellPro Scoring Error")

        if is_single and len(created_records) == 1:
            first = created_records[0]
            return success_response(
                data=first["record"],
                name=first["name"],
                doctype=first["doctype"],
                affected_date=first["affected_date"],
                recalculated_score=recalc_scores.get(first["affected_date"]),
                message=f"Saved to {first['doctype']}"
            )

        return success_response(
            data={
                "created": created_records,
                "count": len(created_records),
                "affected_dates": sorted(list(affected_dates)),
                "recalculated_scores": recalc_scores
            },
            message=f"Successfully processed {len(created_records)} AI domain extractions"
        )
    else:
        for idx, item in enumerate(normalized_records):
            sp_name = f"ai_sp_{idx}"
            frappe.db.savepoint(sp_name)
            try:
                doc, aff_dt = _process_single_insert(
                    doctype=item["doctype"],
                    record_data=item["record_data"],
                    user=user
                )
                affected_dates.add(aff_dt)
                created_records.append({
                    "index": idx,
                    "doctype": item["doctype"],
                    "name": doc.name,
                    "affected_date": aff_dt,
                    "record": doc.as_dict()
                })
            except Exception as ex:
                frappe.db.rollback(save_point=sp_name)
                errors.append({
                    "index": idx,
                    "doctype": item.get("doctype"),
                    "error": str(ex)
                })

        frappe.db.commit()

        recalc_scores = {}
        for dt in affected_dates:
            try:
                recalc_scores[dt] = calculate_daily_score(user, dt)
            except Exception as e:
                frappe.log_error(f"Score recalculation error for {user} on {dt}: {str(e)}", "WellPro Scoring Error")

        return success_response(
            data={
                "created": created_records,
                "errors": errors,
                "successful_count": len(created_records),
                "failed_count": len(errors),
                "affected_dates": sorted(list(affected_dates)),
                "recalculated_scores": recalc_scores
            },
            message=f"Batch processed: {len(created_records)} succeeded, {len(errors)} failed"
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


@frappe.whitelist(methods=["GET", "POST"])
def get_dashboard(as_of_date: Optional[str] = None):
    """
    Returns full multi-dimensional Wellbeing Dashboard data for the authenticated user.
    Includes today score, 30-day exponential recency-weighted score, 7-day, 90-day scores,
    confidences, and trends for Health, Financial, Social, and Overall wellbeing.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Authentication required"), frappe.AuthenticationError)

    target_date = as_of_date or today()
    dashboard_data = get_user_dashboard(user, target_date)
    return success_response(
        data=dashboard_data,
        message="Dashboard metrics retrieved successfully"
    )


@frappe.whitelist(methods=["GET", "POST"])
def get_dashboard_metrics(days: Union[int, str] = 30, as_of_date: Optional[str] = None):
    """
    High-performance dashboard metrics endpoint.
    Recalculates today's / target date score efficiently, computes multi-window recency trends,
    and returns historical score trends alongside recent domain activity feeds.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Authentication required"), frappe.AuthenticationError)

    target_date = as_of_date or today()
    try:
        num_days = min(max(int(days or 30), 1), 365)
    except Exception:
        num_days = 30
    start_date = add_days(target_date, -num_days)

    # 1. Ensure current/target score is fresh and up-to-date
    latest_score = calculate_daily_score(user, target_date)

    # 2. Get multi-window aggregated dashboard metrics (today, 7d, 30d, 90d, trends)
    dashboard_summary = get_user_dashboard(user, target_date)

    # 3. Efficient historical score timeline
    scores = frappe.get_all(
        "Wellbeing Daily Score",
        filters={
            "user": user,
            "score_date": ["between", [start_date, target_date]]
        },
        fields=[
            "score_date", "health_score", "health_confidence",
            "financial_score", "financial_confidence",
            "social_score", "social_confidence", "overall_score"
        ],
        order_by="score_date asc"
    )

    # 4. Concise recent domain records (limit 10 each, selecting client-relevant fields)
    financial = frappe.get_all(
        "Financial Transaction",
        filters={"user": user},
        fields=["name", "transaction_type", "category", "amount", "currency", "transaction_date", "merchant_or_source", "description", "essentiality", "source"],
        order_by="transaction_date desc",
        limit=10
    )
    health = frappe.get_all(
        "Health Daily Record",
        filters={"user": user},
        fields=["name", "record_date", "sleep_hours", "sleep_quality", "steps", "active_minutes", "exercise_minutes", "water_liters", "calories_consumed", "protein_grams", "fruit_veg_servings", "energy_level", "self_rated_health", "source"],
        order_by="record_date desc",
        limit=10
    )
    health_activities = frappe.get_all(
        "Health Activity",
        filters={"user": user},
        fields=["name", "activity_type", "logged_at", "duration_minutes", "distance_km", "steps", "calories_burned", "intensity", "source"],
        order_by="logged_at desc",
        limit=10
    )
    social = frappe.get_all(
        "Social Activity",
        filters={"user": user},
        fields=["name", "logged_at", "interaction_type", "relationship_type", "duration_minutes", "interaction_quality", "connection_level", "mood_after", "notes", "source"],
        order_by="logged_at desc",
        limit=10
    )
    checkins = frappe.get_all(
        "Subjective Wellbeing Checkin",
        filters={"user": user},
        fields=["name", "date", "mood", "energy", "stress", "social_connection", "loneliness", "social_satisfaction", "financial_stress"],
        order_by="date desc",
        limit=10
    )

    return success_response(
        data={
            "current_scores": latest_score,
            "summary": dashboard_summary,
            "historical_trends": scores,
            "financial": financial,
            "health": health,
            "health_activities": health_activities,
            "social": social,
            "checkins": checkins,
            "as_of_date": target_date,
            "days": num_days
        },
        message="Dashboard metrics retrieved successfully"
    )

# -------------------------------------------------------------------
# 7. SCORING GOALS CONFIGURATION APIs
# -------------------------------------------------------------------

@frappe.whitelist(methods=["POST"])
def setup_scoring_goals(
    goals: Optional[Union[Dict[str, Any], str]] = None,
    steps: Optional[Union[int, float, str]] = None,
    budget: Optional[Union[int, float, str]] = None,
    financial_budget: Optional[Union[int, float, str]] = None,
    target_savings_rate: Optional[Union[float, str]] = None,
    savings_rate: Optional[Union[float, str]] = None,
    recalculate: Union[bool, int, str] = True,
    reset: Union[bool, int, str] = False,
    target_user: Optional[str] = None,
    **kwargs
):
    """
    Sets custom wellbeing scoring goals (e.g. 10000 steps, financial budget 10k, 20% savings rate).
    Automatically parses human-friendly inputs (e.g. '10k', '20%', '2500ml', '$10,000') and
    converts them into the exact config scale of values used by the scoring engine.

    If a user has not configured custom goals, the original baseline config heuristics apply.
    """
    import json
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Authentication required"), frappe.AuthenticationError)

    # Multi-user isolation: standard users can only configure their own scoring goals
    effective_user = user
    if target_user and target_user != user:
        if "System Manager" not in frappe.get_roles(user):
            frappe.throw(_("Permission denied: Cannot configure scoring goals for another user"), frappe.PermissionError)
        effective_user = target_user

    is_reset = reset in (True, 1, "1", "true", "True")
    if is_reset:
        profile_name = frappe.db.get_value("WellPro Profile", {"user": effective_user}, "name")
        if profile_name:
            frappe.db.set_value("WellPro Profile", profile_name, "custom_scoring_goals", "{}")
            frappe.db.commit()

        recalc_res = None
        should_recalc = recalculate in (True, 1, "1", "true", "True")
        if should_recalc:
            try:
                recalc_res = calculate_daily_score(effective_user, today())
            except Exception as e:
                frappe.log_error(f"Score recalculation error on goals reset for {effective_user}: {str(e)}", "WellPro Scoring Error")

        return success_response(
            data={
                "user": effective_user,
                "custom_goals": {},
                "effective_config": get_user_scoring_config(effective_user),
                "recalculated_score": recalc_res
            },
            message="Custom scoring goals reset. Default configuration restored."
        )

    # Gather inputs from all supported sources
    raw_input = {}
    try:
        req_json = frappe.request.get_json() if hasattr(frappe, "request") and frappe.request else None
        if isinstance(req_json, dict):
            raw_input.update(req_json)
    except Exception:
        pass

    if goals:
        if isinstance(goals, str):
            try:
                goals_dict = json.loads(goals)
                if isinstance(goals_dict, dict):
                    raw_input.update(goals_dict)
            except Exception:
                pass
        elif isinstance(goals, dict):
            raw_input.update(goals)

    if steps is not None:
        raw_input["steps"] = steps
    if budget is not None:
        raw_input["budget"] = budget
    if financial_budget is not None:
        raw_input["financial_budget"] = financial_budget
    if target_savings_rate is not None:
        raw_input["target_savings_rate"] = target_savings_rate
    if savings_rate is not None:
        raw_input["savings_rate"] = savings_rate

    for k, v in kwargs.items():
        if k not in ("cmd", "target_user", "recalculate", "reset") and v is not None:
            raw_input[k] = v

    converted_goals = parse_custom_goals(raw_input)
    if not converted_goals:
        frappe.throw(
            _("No valid scoring goal parameters provided. Valid options include: steps (e.g. 10k), budget/financial_budget (e.g. 10k), savings_rate (e.g. 20%), active_minutes, exercise_minutes, water, sleep_min, etc."),
            frappe.ValidationError
        )

    # Persist in WellPro Profile
    existing_goals = get_user_custom_goals(effective_user)
    existing_goals.update(converted_goals)
    goals_json = json.dumps(existing_goals)

    profile_name = frappe.db.get_value("WellPro Profile", {"user": effective_user}, "name")
    if profile_name:
        frappe.db.set_value("WellPro Profile", profile_name, "custom_scoring_goals", goals_json)
    else:
        profile_doc = frappe.get_doc({
            "doctype": "WellPro Profile",
            "user": effective_user,
            "custom_scoring_goals": goals_json
        })
        profile_doc.insert(ignore_permissions=True)

    # If custom budget was configured, synchronize with latest Financial Snapshot
    if "budget_amount" in converted_goals:
        snap_name = frappe.db.get_value(
            "Financial Snapshot",
            {"user": effective_user, "snapshot_date": ["<=", today()]},
            "name",
            order_by="snapshot_date desc"
        )
        if snap_name:
            frappe.db.set_value("Financial Snapshot", snap_name, "budget_amount", converted_goals["budget_amount"])

    frappe.db.commit()

    # Recalculate daily score
    recalculated_score = None
    should_recalc = recalculate in (True, 1, "1", "true", "True")
    if should_recalc:
        try:
            recalculated_score = calculate_daily_score(effective_user, today())
        except Exception as e:
            frappe.log_error(f"Score recalculation error on goal update for {effective_user}: {str(e)}", "WellPro Scoring Error")

    effective_cfg = get_user_scoring_config(effective_user)
    return success_response(
        data={
            "user": effective_user,
            "configured_goals": converted_goals,
            "all_custom_goals": existing_goals,
            "effective_config": effective_cfg,
            "recalculated_score": recalculated_score
        },
        message="Scoring goals updated and converted to config scale successfully"
    )


@frappe.whitelist(methods=["POST"])
def set_scoring_goals(**kwargs):
    """Alias for setup_scoring_goals."""
    return setup_scoring_goals(**kwargs)


@frappe.whitelist(methods=["GET"])
def get_scoring_goals(target_user: Optional[str] = None):
    """
    Retrieves current custom scoring goals, default baseline heuristics,
    and effective merged scoring config for the user.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Authentication required"), frappe.AuthenticationError)

    effective_user = user
    if target_user and target_user != user:
        if "System Manager" not in frappe.get_roles(user):
            frappe.throw(_("Permission denied: Cannot view scoring goals for another user"), frappe.PermissionError)
        effective_user = target_user

    custom_goals = get_user_custom_goals(effective_user)
    effective_cfg = get_user_scoring_config(effective_user)

    return success_response(
        data={
            "user": effective_user,
            "has_custom_goals": bool(custom_goals),
            "custom_goals": custom_goals,
            "effective_config": effective_cfg,
            "default_config": DEFAULT_SCORING_CONFIG
        },
        message="Scoring goals retrieved successfully"
    )

