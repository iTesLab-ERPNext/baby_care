import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, add_months, today, flt


class ChildSubscription(Document):
    def validate(self):
        self._fetch_plan_details()
        self._calculate_amount()
        self._set_next_billing_date()

    def _fetch_plan_details(self):
        if self.subscription_plan:
            plan = frappe.get_doc("Subscription Plan", self.subscription_plan)
            self.monthly_amount = plan.base_price
            self.currency = plan.currency or frappe.db.get_single_value("Nursery Settings", "default_currency")

    def _calculate_amount(self):
        base = flt(self.monthly_amount)
        disc = flt(self.discount_percent)
        if disc:
            base = base * (1 - disc / 100)
        self.final_amount = base

    def _set_next_billing_date(self):
        if self.start_date and not self.next_billing_date:
            self.next_billing_date = self.start_date

    def on_submit(self):
        self.status = "Active"
        frappe.db.set_value("Child", self.child, "active_subscription", self.name)
        frappe.db.set_value("Child", self.child, "subscription_status", "Active")

    def on_cancel(self):
        self.status = "Cancelled"
        frappe.db.set_value("Child", self.child, "active_subscription", None)
        frappe.db.set_value("Child", self.child, "subscription_status", "Cancelled")

    @frappe.whitelist()
    def generate_invoice(self):
        """Create a Sales Invoice for the current billing period."""
        from baby_care.baby_care_management.utils.billing import create_subscription_invoice
        return create_subscription_invoice(self.name)


def on_submit(doc, method):
    pass


def on_cancel(doc, method):
    pass
