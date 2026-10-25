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
			if val is not None and val != 0 and (val < 1 or val > 5):
				frappe.throw(_("{0} must be between 1 and 5").format(self.meta.get_label(field)), frappe.ValidationError)

		non_neg_fields = [
			"sleep_hours", "steps", "active_minutes", "exercise_minutes",
			"water_liters", "calories_consumed", "protein_grams", "fruit_veg_servings"
		]
		for field in non_neg_fields:
			val = getattr(self, field, None)
			if val is not None and val < 0:
				frappe.throw(_("{0} cannot be negative").format(self.meta.get_label(field)), frappe.ValidationError)

	def after_insert(self):
		"""Trigger score recalculation after a new Health Daily Record is saved."""
		self._recalculate_score()

	def on_update(self):
		"""Trigger score recalculation whenever a Health Daily Record is updated."""
		self._recalculate_score()

	def on_trash(self):
		"""Trigger score recalculation when a Health Daily Record is deleted."""
		self._recalculate_score()

	def _recalculate_score(self):
		"""Recalculate the Wellbeing Daily Score for this record's date."""
		try:
			from well_pro.well_pro_app.services.scoring import calculate_daily_score
			if self.record_date:
				calculate_daily_score(self.user, str(self.record_date))
		except Exception as e:
			frappe.log_error(
				f"Health Daily Record score recalculation failed for {self.user}: {str(e)}",
				"WellPro Scoring Error"
			)
