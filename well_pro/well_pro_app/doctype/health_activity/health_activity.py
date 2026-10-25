# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class HealthActivity(Document):
	def validate(self):
		non_neg_fields = ["duration_minutes", "distance_km", "steps", "calories_burned"]
		for field in non_neg_fields:
			val = getattr(self, field, None)
			if val is not None and val < 0:
				frappe.throw(_("{0} cannot be negative").format(self.meta.get_label(field)), frappe.ValidationError)

	def after_insert(self):
		"""Trigger daily record accumulation and score recalculation."""
		self._sync_and_recalculate()

	def on_update(self):
		"""Trigger daily record accumulation and score recalculation."""
		self._sync_and_recalculate()

	def on_trash(self):
		"""Trigger daily record accumulation and score recalculation."""
		self._sync_and_recalculate()

	def _sync_and_recalculate(self):
		"""Accumulate into Health Daily Record and recalculate score."""
		try:
			from well_pro.well_pro_app.services.scoring import accumulate_daily_health_record, calculate_daily_score
			affected_date = None
			if self.logged_at:
				affected_date = str(getdate(self.logged_at))
			if affected_date:
				accumulate_daily_health_record(self.user, affected_date)
				calculate_daily_score(self.user, affected_date)
		except Exception as e:
			frappe.log_error(
				f"Health Activity sync/recalculation failed for {self.user}: {str(e)}",
				"WellPro Scoring Error"
			)
