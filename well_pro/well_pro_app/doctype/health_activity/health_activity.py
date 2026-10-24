# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class HealthActivity(Document):
	def validate(self):
		non_neg_fields = ["duration_minutes", "distance_km", "steps", "calories_burned"]
		for field in non_neg_fields:
			val = getattr(self, field, None)
			if val is not None and val < 0:
				frappe.throw(_("{0} cannot be negative").format(self.meta.get_label(field)), frappe.ValidationError)
