import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class AgeGroup(Document):
    def validate(self):
        lo, hi = cint(self.min_age_months), cint(self.max_age_months)
        if lo < 0 or hi < 0:
            frappe.throw(_("Ages cannot be negative."))
        if hi and lo >= hi:
            frappe.throw(_("Minimum age must be less than maximum age (leave maximum at 0 for no upper limit)."))
