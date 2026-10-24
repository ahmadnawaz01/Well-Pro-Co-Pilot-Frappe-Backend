# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class HealthDailyRecord(Document):
	def validate(self):
		self.validate_unique_date()
		self.validate_ranges()

	def validate_unique_date(self):
		existing = frappe.db.exists(
			"Health Daily Record",
			{"user": self.user, "record_date": self.record_date}
		)
		if existing and existing != self.name:
			frappe.throw(
				_("A Health Daily Record already exists for user {0} on {1}").format(self.user, self.record_date),
				frappe.DuplicateEntryError
			)

	def validate_ranges(self):
		rating_fields = ["sleep_quality", "energy_level", "self_rated_health"]
		for field in rating_fields:
			val = getattr(self, field, None)
			if val is not None and (val < 1 or val > 5):
				frappe.throw(_("{0} must be between 1 and 5").format(self.meta.get_label(field)), frappe.ValidationError)

		non_neg_fields = [
			"sleep_hours", "steps", "active_minutes", "exercise_minutes",
			"water_liters", "calories_consumed", "protein_grams", "fruit_veg_servings"
		]
		for field in non_neg_fields:
			val = getattr(self, field, None)
			if val is not None and val < 0:
				frappe.throw(_("{0} cannot be negative").format(self.meta.get_label(field)), frappe.ValidationError)
