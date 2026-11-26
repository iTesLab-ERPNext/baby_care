import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, flt, getdate

from baby_care.baby_care_management.utils import billing


class NurseryInvoice(Document):
    def validate(self):
        s = frappe.get_cached_doc("Nursery Settings")
        self.currency = self.currency or billing.default_currency()
        if not self.due_date:
            self.due_date = add_days(self.posting_date, cint(s.invoice_due_days) or 15)
        if getdate(self.due_date) < getdate(self.posting_date):
            frappe.throw(_("Due date cannot be before the invoice date."))
        self._validate_child()
        self._validate_duplicate_period()
        self._calculate()
        self.status = "Draft"

    def _validate_child(self):
        if not self.child:
            return
        parents = frappe.get_all("Child Parent Link", filters={"parent": self.child, "parenttype": "Child"}, pluck="parent_profile")
        if self.parent_profile not in parents:
            frappe.throw(_("{0} is not linked as a parent of child {1}.").format(self.parent_name or self.parent_profile, self.child))

    def _validate_duplicate_period(self):
        if not (self.child_subscription and self.billing_period):
            return
        other = frappe.db.get_value("Nursery Invoice", {"child_subscription": self.child_subscription, "billing_period": self.billing_period,
                                                        "docstatus": ("<", 2), "name": ("!=", self.name)}, "name")
        if other:
            frappe.throw(_("Billing period {0} is already invoiced ({1}).").format(self.billing_period, other), title=_("Duplicate invoice"))

    def _calculate(self):
        total = 0
        for row in self.items:
            row.qty = flt(row.qty) or 1
            row.amount = flt(flt(row.rate) * row.qty, 2)
            total += row.amount
        if not 0 <= flt(self.discount_percent) <= 100:
            frappe.throw(_("Discount must be between 0 and 100%."))
        if flt(self.tax_rate) < 0:
            frappe.throw(_("Tax cannot be negative."))
        self.total = flt(total, 2)
        self.discount_amount = flt(self.total * flt(self.discount_percent) / 100, 2)
        self.tax_amount = flt((self.total - self.discount_amount) * flt(self.tax_rate) / 100, 2)
        self.grand_total = flt(self.total - self.discount_amount + self.tax_amount, 2)
        if self.grand_total < 0:
            frappe.throw(_("The invoice total cannot be negative."))
        self.paid_amount = 0
        self.outstanding_amount = self.grand_total

    def on_submit(self):
        self.db_set("status", billing.invoice_status(self.grand_total, self.outstanding_amount, self.due_date))
        billing.sync_subscription_row(self.name, self.status, self.grand_total)

    def before_cancel(self):
        payments = frappe.db.sql_list(
            """select distinct p.name from `tabNursery Payment Allocation` a join `tabNursery Payment` p on p.name = a.parent
               where a.invoice = %s and p.docstatus = 1""", self.name)
        if payments:
            frappe.throw(_("Cancel the payments of this invoice first: {0}").format(", ".join(payments)))

    def on_cancel(self):
        self.db_set({"status": "Cancelled", "outstanding_amount": 0})
        billing.sync_subscription_row(self.name, "Cancelled")


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def children_of_parent(doctype, txt, searchfield, start, page_len, filters):
    names = frappe.get_all("Child Parent Link", filters={"parent_profile": filters.get("parent_profile"), "parenttype": "Child"}, pluck="parent")
    return frappe.get_list("Child", filters={"name": ("in", names or [""]), "full_name": ("like", f"%{txt}%")},
                           fields=["name", "full_name"], start=start, page_length=page_len, as_list=True)
