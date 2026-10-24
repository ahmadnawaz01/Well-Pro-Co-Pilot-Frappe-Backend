# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class FinancialSnapshot(Document):
	def validate(self):
		non_neg_fields = [
			"monthly_income", "monthly_expenses", "essential_monthly_expenses",
			"liquid_savings", "investment_value", "emergency_fund",
			"budget_amount", "outstanding_debt", "monthly_debt_payment"
		]
		for field in non_neg_fields:
			val = getattr(self, field, None)
			if val is not None and val < 0:
				frappe.throw(_("{0} cannot be negative").format(self.meta.get_label(field)), frappe.ValidationError)

		if self.financial_stress_rating is not None and (self.financial_stress_rating < 1 or self.financial_stress_rating > 5):
			frappe.throw(_("Financial Stress Rating must be between 1 and 5"), frappe.ValidationError)
