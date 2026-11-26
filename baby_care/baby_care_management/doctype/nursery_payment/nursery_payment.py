import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from baby_care.baby_care_management.utils import billing


class NurseryPayment(Document):
    def validate(self):
        self.currency = self.currency or billing.default_currency()
        if flt(self.amount) <= 0:
            frappe.throw(_("The amount received must be greater than zero."))
        if not self.allocations:
            self.allocate_oldest_first()
        self._validate_allocations()

    def allocate_oldest_first(self):
        """Spread the amount over the parent's unpaid invoices, oldest due date first."""
        self.set("allocations", [])
        left = flt(self.amount)
        for inv in billing.open_invoices(self.parent_profile, exclude_payment=self.name):
            if left <= 0:
                break
            take = min(left, flt(inv.outstanding_amount))
            if take > 0:
                self.append("allocations", {"invoice": inv.name, "allocated_amount": flt(take, 2)})
                left -= take

    def _validate_allocations(self):
        allow_partial = frappe.db.get_single_value("Nursery Settings", "allow_partial_payment")
        seen, total = set(), 0
        for row in self.allocations:
            if row.invoice in seen:
                frappe.throw(_("Row {0}: invoice {1} is listed twice.").format(row.idx, row.invoice))
            seen.add(row.invoice)
            inv = frappe.db.get_value("Nursery Invoice", row.invoice, ["parent_profile", "docstatus", "grand_total", "child", "currency"], as_dict=True)
            if not inv or inv.docstatus != 1:
                frappe.throw(_("Row {0}: invoice {1} is not submitted.").format(row.idx, row.invoice))
            if inv.parent_profile != self.parent_profile:
                frappe.throw(_("Row {0}: invoice {1} belongs to another parent.").format(row.idx, row.invoice))
            if inv.currency != self.currency:
                frappe.throw(_("Row {0}: invoice {1} is in {2}.").format(row.idx, row.invoice, inv.currency))
            row.child = inv.child
            row.invoice_total = inv.grand_total
            row.outstanding = flt(flt(inv.grand_total) - billing.paid_on_invoice(row.invoice, exclude_payment=self.name), 2)
            if flt(row.allocated_amount) <= 0:
                frappe.throw(_("Row {0}: the allocated amount must be greater than zero.").format(row.idx))
            if flt(row.allocated_amount, 2) > flt(row.outstanding, 2):
                frappe.throw(_("Row {0}: {1} is more than the {2} left to pay on invoice {3}.").format(
                    row.idx, frappe.format(row.allocated_amount, {"fieldtype": "Currency", "options": self.currency}),
                    frappe.format(row.outstanding, {"fieldtype": "Currency", "options": self.currency}), row.invoice))
            if not allow_partial and flt(row.allocated_amount, 2) < flt(row.outstanding, 2):
                frappe.throw(_("Row {0}: partial payments are switched off in Nursery Settings.").format(row.idx))
            total += flt(row.allocated_amount)
        if flt(total, 2) > flt(self.amount, 2):
            frappe.throw(_("The allocated total ({0}) is more than the amount received ({1}).").format(flt(total, 2), flt(self.amount, 2)))
        self.allocated_amount = flt(total, 2)
        self.unallocated_amount = flt(flt(self.amount) - total, 2)

    def on_submit(self):
        self._update_invoices()

    def on_cancel(self):
        self._update_invoices()

    def _update_invoices(self):
        for row in self.allocations:
            billing.update_invoice_balance(row.invoice)


@frappe.whitelist()
def get_open_invoices(parent_profile, payment=None):
    frappe.has_permission("Nursery Invoice", "read", throw=True)
    return billing.open_invoices(parent_profile, exclude_payment=payment)
