import frappe
from frappe.model.document import Document


class AgeGroup(Document):
    def validate(self):
        if self.min_age_months >= self.max_age_months:
            frappe.throw(frappe._("Minimum age must be less than maximum age."))
