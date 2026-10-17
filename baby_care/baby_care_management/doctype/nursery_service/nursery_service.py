import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate


class NurseryService(Document):
    def validate(self):
        if flt(self.price) < 0:
            frappe.throw(_("Service price cannot be negative."))
        if self.pricing_method == "Included in Subscription":
            self.billing_frequency = "Included"
        if self.end_date and self.start_date and getdate(self.end_date) < getdate(self.start_date):
            frappe.throw(_("End date cannot be before start date."))

    def is_available_on(self, date):
        date = getdate(date)
        if not self.is_active:
            return False
        if self.start_date and date < getdate(self.start_date):
            return False
        if self.end_date and date > getdate(self.end_date):
            return False
        return True
