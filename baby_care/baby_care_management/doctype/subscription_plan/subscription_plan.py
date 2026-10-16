import frappe
from frappe import _
from frappe.model.document import Document


class SubscriptionPlan(Document):
    def validate(self):
        if self.base_price < 0:
            frappe.throw(_("Base Price cannot be negative."))
        if self.billing_frequency == "Custom" and not self.duration_months:
            frappe.throw(_("Duration (Months) is required for Custom billing frequency."))
