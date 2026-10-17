import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class SubscriptionPlan(Document):
    def validate(self):
        if flt(self.base_price) < 0:
            frappe.throw(_("Base Price cannot be negative."))
        if self.billing_frequency == "Custom" and not self.duration_months:
            frappe.throw(_("Duration (Months) is required for Custom billing frequency."))
        for pct, label in ((self.multi_child_discount_override, _("Multi-child discount")),
                           (self.early_payment_discount_percent, _("Early payment discount"))):
            if not 0 <= flt(pct) <= 100:
                frappe.throw(_("{0} must be between 0 and 100%.").format(label))
        seen = set()
        for row in self.services or []:
            if row.service in seen:
                frappe.throw(_("Service {0} is listed twice.").format(row.service))
            seen.add(row.service)
