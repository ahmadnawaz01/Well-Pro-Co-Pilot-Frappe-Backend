# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class SocialActivity(Document):
	def validate(self):
		rating_fields = ["interaction_quality", "connection_level", "mood_after"]
		for field in rating_fields:
			val = getattr(self, field, None)
			if val is not None and val != 0 and (val < 1 or val > 5):
				frappe.throw(_("{0} must be between 1 and 5").format(self.meta.get_label(field)), frappe.ValidationError)

		if self.duration_minutes is not None and self.duration_minutes < 0:
			frappe.throw(_("Duration cannot be negative"), frappe.ValidationError)

	def after_insert(self):
		"""Trigger score recalculation after a new Social Activity is saved."""
		self._recalculate_score()

	def on_update(self):
		"""Trigger score recalculation whenever a Social Activity is updated."""
		self._recalculate_score()

	def on_trash(self):
		"""Trigger score recalculation when a Social Activity is deleted."""
		self._recalculate_score()

	def _recalculate_score(self):
		"""Recalculate the Wellbeing Daily Score for the activity's date."""
		try:
			from well_pro.well_pro_app.services.scoring import calculate_daily_score
			affected_date = None
			if self.logged_at:
				affected_date = str(getdate(self.logged_at))
			if affected_date:
				calculate_daily_score(self.user, affected_date)
		except Exception as e:
			frappe.log_error(
				f"Social Activity score recalculation failed for {self.user}: {str(e)}",
				"WellPro Scoring Error"
			)
