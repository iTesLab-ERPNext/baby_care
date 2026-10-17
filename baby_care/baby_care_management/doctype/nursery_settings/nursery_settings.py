import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt


class NurserySettings(Document):
    def validate(self):
        if not 0 <= cint(self.invoice_generation_day) <= 60:
            frappe.throw(_("Invoice lead time must be between 0 and 60 days."))
        if not 0 <= flt(self.multi_child_discount_percent) <= 100:
            frappe.throw(_("Multi-Child Discount must be between 0 and 100."))
        for fn in ("notify_subscription_expiry_days", "notify_document_expiry_days", "notify_overdue_after_days", "invoice_due_days"):
            if cint(self.get(fn)) < 0:
                frappe.throw(_("{0} cannot be negative.").format(self.meta.get_label(fn)))
