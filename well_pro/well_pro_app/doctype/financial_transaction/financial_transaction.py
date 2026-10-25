# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class FinancialTransaction(Document):
	def validate(self):
		if self.amount is not None and self.amount <= 0:
			frappe.throw(_("Transaction amount must be greater than zero"), frappe.ValidationError)

	def after_insert(self):
		"""Trigger daily snapshot accumulation and score recalculation."""
		self._sync_and_recalculate()

	def on_update(self):
		"""Trigger daily snapshot accumulation and score recalculation."""
		self._sync_and_recalculate()

	def on_trash(self):
		"""Trigger daily snapshot accumulation and score recalculation."""
		self._sync_and_recalculate()

	def _sync_and_recalculate(self):
		"""Accumulate into Financial Snapshot and recalculate score."""
		try:
			from well_pro.well_pro_app.services.scoring import accumulate_daily_financial_snapshot, calculate_daily_score
			if self.transaction_date:
				t_date = str(self.transaction_date)
				accumulate_daily_financial_snapshot(self.user, t_date)
				calculate_daily_score(self.user, t_date)
		except Exception as e:
			frappe.log_error(
				f"Financial Transaction sync/recalculation failed for {self.user}: {str(e)}",
				"WellPro Scoring Error"
			)
