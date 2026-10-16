import frappe
from frappe.model.document import Document


class NurserySettings(Document):
    def validate(self):
        if self.invoice_generation_day and not (1 <= self.invoice_generation_day <= 28):
            frappe.throw(frappe._("Invoice Generation Day must be between 1 and 28."))
        if self.multi_child_discount_percent and not (0 <= self.multi_child_discount_percent <= 100):
            frappe.throw(frappe._("Multi-Child Discount must be between 0 and 100."))
