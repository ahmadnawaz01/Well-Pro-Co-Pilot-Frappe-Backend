# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class WellbeingDailyScore(Document):
	def validate(self):
		score_fields = [
			"health_score", "health_confidence",
			"financial_score", "financial_confidence",
			"social_score", "social_confidence",
			"overall_score"
		]
		for field in score_fields:
			val = getattr(self, field, None)
			if val is not None and (val < 0.0 or val > 100.0):
				frappe.throw(_("{0} must be between 0 and 100").format(self.meta.get_label(field)), frappe.ValidationError)
