# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class SubjectiveWellbeingCheckin(Document):
	def validate(self):
		self.validate_unique_date()
		self.validate_ratings()

	def validate_unique_date(self):
		existing = frappe.db.exists(
			"Subjective Wellbeing Checkin",
			{"user": self.user, "date": self.date}
		)
		if existing and existing != self.name:
			frappe.throw(
				_("A Subjective Wellbeing Checkin already exists for user {0} on {1}").format(self.user, self.date),
				frappe.DuplicateEntryError
			)

	def validate_ratings(self):
		rating_fields = [
			"mood", "energy", "stress", "social_connection",
			"loneliness", "social_satisfaction", "financial_stress"
		]
		for field in rating_fields:
			val = getattr(self, field, None)
			if val is not None and val != 0 and (val < 1 or val > 5):
				frappe.throw(_("{0} must be between 1 and 5").format(self.meta.get_label(field)), frappe.ValidationError)

	def after_insert(self):
		self._recalculate_score()

	def on_update(self):
		self._recalculate_score()

	def on_trash(self):
		self._recalculate_score()

	def _recalculate_score(self):
		try:
			from well_pro.well_pro_app.services.scoring import calculate_daily_score
			if self.date:
				calculate_daily_score(self.user, str(self.date))
		except Exception as e:
			frappe.log_error(
				f"Subjective Checkin score recalculation failed for {self.user}: {str(e)}",
				"WellPro Scoring Error"
			)
