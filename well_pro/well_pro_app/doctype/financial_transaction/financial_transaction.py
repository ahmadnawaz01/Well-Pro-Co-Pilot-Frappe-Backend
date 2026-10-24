# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class FinancialTransaction(Document):
	def validate(self):
		if self.amount is not None and self.amount <= 0:
			frappe.throw(_("Transaction amount must be greater than zero"), frappe.ValidationError)
