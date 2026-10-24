"""
WellPro Development & Testing Data Seed Script
Generates comprehensive representative test data for:
- User A (30 days of continuous health, financial, social, and check-in records with calculated scores)
- User B (Security isolation and edge-case partial/missing data test suite)
- Standard Financial Categories
Usage:
  bench --site <site> execute well_pro.well_pro_app.seed.seed_development_data
"""
from datetime import date, timedelta
import frappe
from frappe.utils import today, add_days
from well_pro.well_pro_app.services.scoring import calculate_daily_score


def seed_development_data():
    """Seeds database with complete representative development data."""
    frappe.set_user("Administrator")
    print("Beginning WellPro Development Data Seeding...")

    # 1. Seed Financial Categories
    categories = [
        {"category_name": "Salary & Wages", "category_type": "Income", "description": "Primary employment income"},
        {"category_name": "Freelance & Consulting", "category_type": "Income", "description": "Secondary side-hustle income"},
        {"category_name": "Groceries & Food", "category_type": "Expense", "description": "Essential groceries and nutrition"},
        {"category_name": "Rent & Housing", "category_type": "Expense", "description": "Monthly rent and housing costs"},
        {"category_name": "Utilities & Bills", "category_type": "Expense", "description": "Electricity, water, internet bills"},
        {"category_name": "Dining & Social", "category_type": "Expense", "description": "Social dining and restaurants"},
        {"category_name": "Health & Fitness", "category_type": "Expense", "description": "Gym memberships and wellness"},
        {"category_name": "Index Fund Investment", "category_type": "Investment", "description": "Long-term index fund DCA"},
        {"category_name": "Student Loan Payment", "category_type": "Debt", "description": "Monthly student debt service"},
        {"category_name": "Emergency Fund Transfer", "category_type": "Transfer", "description": "Transfer to high-yield savings"}
    ]

    for cat in categories:
        if not frappe.db.exists("Financial Category", {"category_name": cat["category_name"]}):
            doc = frappe.get_doc({
                "doctype": "Financial Category",
                "active": 1,
                **cat
            })
            doc.insert(ignore_permissions=True)
            print(f"Created category: {cat['category_name']}")
    frappe.db.commit()

    # 2. Seed Users
    user_a = "user_a@wellpro.test"
    user_b = "user_b@wellpro.test"

    for email, fname, lname in [(user_a, "Avery", "Active"), (user_b, "Blake", "Boundary")]:
        if not frappe.db.exists("User", email):
            u_doc = frappe.get_doc({
                "doctype": "User",
                "email": email,
                "first_name": fname,
                "last_name": lname,
                "enabled": 1,
                "send_welcome_email": 0,
                "user_type": "System User"
            }).insert(ignore_permissions=True)
            u_doc.new_password = "WellProPassword123!"
            u_doc.api_key = frappe.generate_hash(length=15)
            u_doc.api_secret = frappe.generate_hash(length=15)
            u_doc.save(ignore_permissions=True)
            print(f"Created user: {email}")

        if not frappe.db.exists("WellPro Profile", {"user": email}):
            frappe.get_doc({
                "doctype": "WellPro Profile",
                "user": email,
                "timezone": "UTC",
                "date_of_birth": "1992-05-14",
                "height_cm": 175.0,
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
                "allow_ai_processing": 1,
                "consent_version": "v1.0"
            }).insert(ignore_permissions=True)

    frappe.db.commit()

    # 3. Seed User A: 30 Continuous Days of Rich Data
    today_dt = date.today()
    print(f"Generating 30 days of data for {user_a} ending on {today_dt}...")

    # Financial Snapshots for User A: 1 from 30 days ago, 1 current
    snap1_date = str(today_dt - timedelta(days=30))
    if not frappe.db.exists("Financial Snapshot", {"user": user_a, "snapshot_date": snap1_date}):
        frappe.get_doc({
            "doctype": "Financial Snapshot",
            "user": user_a,
            "snapshot_date": snap1_date,
            "monthly_income": 6500.0,
            "monthly_expenses": 4200.0,
            "essential_monthly_expenses": 3000.0,
            "liquid_savings": 18000.0,
            "investment_value": 25000.0,
            "emergency_fund": 18000.0,
            "budget_amount": 4500.0,
            "outstanding_debt": 8000.0,
            "monthly_debt_payment": 600.0,
            "financial_stress_rating": 2,
            "source": "Manual Entry"
        }).insert(ignore_permissions=True)

    snap2_date = str(today_dt - timedelta(days=2))
    if not frappe.db.exists("Financial Snapshot", {"user": user_a, "snapshot_date": snap2_date}):
        frappe.get_doc({
            "doctype": "Financial Snapshot",
            "user": user_a,
            "snapshot_date": snap2_date,
            "monthly_income": 7000.0,
            "monthly_expenses": 4100.0,
            "essential_monthly_expenses": 3000.0,
            "liquid_savings": 22000.0,
            "investment_value": 31000.0,
            "emergency_fund": 20000.0,
            "budget_amount": 4500.0,
            "outstanding_debt": 6800.0,
            "monthly_debt_payment": 600.0,
            "financial_stress_rating": 1,
            "source": "Manual Entry"
        }).insert(ignore_permissions=True)

    # Financial Transactions for User A (spread over the 30 days)
       # Financial Transactions for User A (spread over the 30 days)
    transactions_template = [
        ("Salary & Wages", "Income", 3500.0, 28, "Bi-weekly paycheck"),
        ("Groceries & Food", "Expense", 145.20, 27, "Weekly organic groceries"),
        ("Rent & Housing", "Expense", 1600.0, 26, "Monthly apartment rent"),
        ("Utilities & Bills", "Expense", 120.50, 24, "Electric and broadband"),
        ("Dining & Social", "Expense", 65.00, 22, "Dinner with teammates"),
        ("Student Loan Payment", "Debt Payment", 300.0, 21, "Monthly loan repayment"), # <-- Change "Debt" to "Debt Payment"
        ("Index Fund Investment", "Investment", 500.0, 20, "Vanguard S&P 500 DCA"),
        ("Health & Fitness", "Expense", 85.00, 18, "Gym membership renewal"),
        ("Groceries & Food", "Expense", 162.40, 17, "Whole Foods groceries"),
        ("Salary & Wages", "Income", 3500.0, 14, "Bi-weekly paycheck"),
        ("Freelance & Consulting", "Income", 850.0, 13, "Frontend web audit fee"),
        ("Emergency Fund Transfer", "Transfer", 400.0, 12, "Savings transfer"),
        ("Dining & Social", "Expense", 42.00, 11, "Coffee and lunch"),
        ("Student Loan Payment", "Debt Payment", 300.0, 9, "Monthly student loan"),    # <-- Change "Debt" to "Debt Payment"
        ("Index Fund Investment", "Investment", 500.0, 8, "Monthly index allocation"),
        ("Groceries & Food", "Expense", 138.90, 7, "Weekly groceries"),
        ("Dining & Social", "Expense", 88.00, 5, "Birthday celebration"),
        ("Health & Fitness", "Expense", 45.00, 4, "Supplements & electrolyte"),
        ("Groceries & Food", "Expense", 112.30, 2, "Farmer market supplies"),
        ("Freelance & Consulting", "Income", 600.0, 1, "Technical writing honorarium")
    ]


    for cat_name, tx_type, amt, days_back, desc in transactions_template:
        t_date = str(today_dt - timedelta(days=days_back))
        cat_id = frappe.db.get_value("Financial Category", {"category_name": cat_name}, "name") or cat_name
        if not frappe.db.exists("Financial Transaction", {"user": user_a, "transaction_date": t_date, "amount": amt}):
            frappe.get_doc({
                "doctype": "Financial Transaction",
                "user": user_a,
                "transaction_type": tx_type,
                "category": cat_id,
                "amount": amt,
                "transaction_date": t_date,
                "merchant_or_source": desc.split()[0],
                "description": desc,
                "payment_method": "Bank" if "Salary" in cat_name else "Card",
                "essentiality": "Essential" if tx_type in ["Debt"] or "Rent" in cat_name or "Groceries" in cat_name else "Discretionary",
                "source": "Manual Entry"
            }).insert(ignore_permissions=True)

    # 30 Days of Health Records, Activities, Social Activities, and Checkins for User A
    for d in range(30, -1, -1):
        curr_date = today_dt - timedelta(days=d)
        curr_str = str(curr_date)

        # Health Daily Record
        # Vary sleep (7.0 - 8.5 hrs), steps (8,000 - 12,500), water (2.2 - 3.0L)
        sleep_hrs = round(7.0 + (d % 4) * 0.5, 1)
        steps_val = 8500 + ((d * 37) % 4500)
        exercise_mins = 30 + ((d * 7) % 35)

        if not frappe.db.exists("Health Daily Record", {"user": user_a, "record_date": curr_str}):
            frappe.get_doc({
                "doctype": "Health Daily Record",
                "user": user_a,
                "record_date": curr_str,
                "sleep_hours": sleep_hrs,
                "sleep_quality": 4 if sleep_hrs >= 7.5 else 3,
                "steps": steps_val,
                "active_minutes": 35,
                "exercise_minutes": exercise_mins,
                "exercise_intensity": "Moderate",
                "water_liters": 2.6,
                "calories_consumed": 2150.0,
                "protein_grams": 75.0,
                "fruit_veg_servings": 5.0,
                "energy_level": 4,
                "self_rated_health": 4,
                "source": "Wearable"
            }).insert(ignore_permissions=True)

        # Health Activity (on ~15 alternate days)
        if d % 2 == 0:
            act_time = f"{curr_str} 07:30:00"
            if not frappe.db.exists("Health Activity", {"user": user_a, "logged_at": act_time}):
                frappe.get_doc({
                    "doctype": "Health Activity",
                    "user": user_a,
                    "activity_type": "Running" if d % 4 == 0 else "Gym",
                    "logged_at": act_time,
                    "duration_minutes": float(exercise_mins),
                    "distance_km": 5.2 if d % 4 == 0 else 0.0,
                    "steps": 4500,
                    "calories_burned": 380.0,
                    "intensity": "High" if d % 4 == 0 else "Moderate",
                    "source": "Wearable"
                }).insert(ignore_permissions=True)

        # Social Activity (on ~15 alternate days)
        if (d + 1) % 2 == 0:
            soc_time = f"{curr_str} 19:00:00"
            if not frappe.db.exists("Social Activity", {"user": user_a, "logged_at": soc_time}):
                frappe.get_doc({
                    "doctype": "Social Activity",
                    "user": user_a,
                    "logged_at": soc_time,
                    "interaction_type": "In Person",
                    "relationship_type": "Friend" if d % 3 == 0 else "Family",
                    "duration_minutes": 90.0,
                    "interaction_quality": 5 if d % 5 != 0 else 4,
                    "connection_level": 4,
                    "mood_after": 5,
                    "notes": "Meaningful dinner conversation and catch-up",
                    "source": "Manual Entry"
                }).insert(ignore_permissions=True)

        # Subjective Wellbeing Check-in (for 25 of 30 days)
        if d <= 25:
            if not frappe.db.exists("Subjective Wellbeing Checkin", {"user": user_a, "date": curr_str}):
                frappe.get_doc({
                    "doctype": "Subjective Wellbeing Checkin",
                    "user": user_a,
                    "date": curr_str,
                    "mood": 4,
                    "energy": 4,
                    "stress": 2,
                    "social_connection": 4,
                    "loneliness": 1,  # 1 = low loneliness/best
                    "social_satisfaction": 4,
                    "financial_stress": 1
                }).insert(ignore_permissions=True)

        # Calculate and store score for this date
        calculate_daily_score(user_a, curr_str)

    frappe.db.commit()
    print(f"User A ({user_a}) successfully seeded with 30 days of data and calculated scores.")

    # 4. Seed User B: Edge Cases and Isolation Test Data
    print(f"Generating security and missing-data edge cases for {user_b}...")
    edge_dates = [
        # (date_offset, desc, health_record, checkin, snapshot)
        (
            1, "Day 1: No Sleep Recorded",
            {"record_date": str(today_dt - timedelta(days=1)), "steps": 7000, "water_liters": 2.0},
            {"mood": 3, "energy": 2, "stress": 3, "social_connection": 3, "loneliness": 2, "social_satisfaction": 3},
            None
        ),
        (
            2, "Day 2: Only Health Data, Zero Financial and Social",
            {"record_date": str(today_dt - timedelta(days=2)), "sleep_hours": 8.0, "sleep_quality": 4, "steps": 10500, "water_liters": 2.5},
            None,
            None
        ),
        (
            3, "Day 3: Only Social Data, Zero Health Data",
            None,
            {"mood": 4, "energy": 4, "stress": 2, "social_connection": 5, "loneliness": 1, "social_satisfaction": 5},
            None
        ),
        (
            4, "Day 4: Financial Snapshot Missing Income (Only Emergency Fund & Debt)",
            {"record_date": str(today_dt - timedelta(days=4)), "sleep_hours": 6.5, "steps": 6000},
            {"mood": 2, "energy": 2, "stress": 4, "social_connection": 2, "loneliness": 4, "financial_stress": 4},
            {
                "snapshot_date": str(today_dt - timedelta(days=4)),
                "monthly_income": 0.0,
                "monthly_expenses": 2500.0,
                "essential_monthly_expenses": 1800.0,
                "liquid_savings": 5000.0,
                "outstanding_debt": 15000.0,
                "financial_stress_rating": 4
            }
        ),
        (
            5, "Day 5: Severe Loneliness Check-in",
            {"record_date": str(today_dt - timedelta(days=5)), "sleep_hours": 5.0, "steps": 3000},
            {"mood": 1, "energy": 1, "stress": 5, "social_connection": 1, "loneliness": 5, "social_satisfaction": 1},
            None
        )
    ]

    for days_back, desc, h_data, c_data, s_data in edge_dates:
        t_str = str(today_dt - timedelta(days=days_back))
        if h_data:
            if not frappe.db.exists("Health Daily Record", {"user": user_b, "record_date": t_str}):
                frappe.get_doc({
                    "doctype": "Health Daily Record",
                    "user": user_b,
                    **h_data
                }).insert(ignore_permissions=True)

        if c_data:
            if not frappe.db.exists("Subjective Wellbeing Checkin", {"user": user_b, "date": t_str}):
                frappe.get_doc({
                    "doctype": "Subjective Wellbeing Checkin",
                    "user": user_b,
                    "date": t_str,
                    **c_data
                }).insert(ignore_permissions=True)

        if s_data:
            if not frappe.db.exists("Financial Snapshot", {"user": user_b, "snapshot_date": t_str}):
                frappe.get_doc({
                    "doctype": "Financial Snapshot",
                    "user": user_b,
                    **s_data
                }).insert(ignore_permissions=True)

        calculate_daily_score(user_b, t_str)

    frappe.db.commit()
    print(f"User B ({user_b}) successfully seeded with edge-case missing data scenarios.")
    print("Seeding completed successfully!")


if __name__ == "__main__":
    seed_development_data()
