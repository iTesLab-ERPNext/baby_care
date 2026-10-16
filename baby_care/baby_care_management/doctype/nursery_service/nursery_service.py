import frappe
from frappe import _
from frappe.model.document import Document


class NurseryService(Document):
    def validate(self):
        if self.price and self.price < 0:
            frappe.throw(_("Service price cannot be negative."))
        if self.end_date and self.start_date and self.end_date < self.start_date:
            frappe.throw(_("End date cannot be before start date."))
