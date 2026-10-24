# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class WellProProfile(Document):
	def validate(self):
		if self.height_cm is not None and self.height_cm <= 0:
			frappe.throw(_("Height must be greater than zero"), frappe.ValidationError)
