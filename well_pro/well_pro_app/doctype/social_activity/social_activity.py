# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class SocialActivity(Document):
	def validate(self):
		rating_fields = ["interaction_quality", "connection_level", "mood_after"]
		for field in rating_fields:
			val = getattr(self, field, None)
			if val is not None and (val < 1 or val > 5):
				frappe.throw(_("{0} must be between 1 and 5").format(self.meta.get_label(field)), frappe.ValidationError)

		if self.duration_minutes is not None and self.duration_minutes < 0:
			frappe.throw(_("Duration cannot be negative"), frappe.ValidationError)
