import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, add_months, cint, flt, getdate, today

OPEN_STATUSES = ("Active", "Pending", "Suspended")
FREQUENCY_MONTHS = {"Monthly": 1, "Quarterly": 3, "Annual": 12}


def plan_period_months(plan):
    return FREQUENCY_MONTHS.get(plan.billing_frequency) or max(cint(plan.duration_months), 1)


class ChildSubscription(Document):
    @property
    def plan(self):
        return frappe.get_cached_doc("Subscription Plan", self.subscription_plan)

    def validate(self):
        self._validate_parent()
        self._validate_plan()
        self._set_dates()
        self._validate_overlap()
        self._set_discount()
        self._calculate_amount()
        if self.docstatus == 0:
            self.status = "Draft"

    def before_submit(self):
        self.status = "Active" if getdate(self.start_date) <= getdate(today()) else "Pending"

    def on_submit(self):
        self._update_child()

    def on_cancel(self):
        self.db_set("status", "Cancelled")
        self._update_child()

    def on_update_after_submit(self):
        self._update_child()

    # ── validation ───────────────────────────────────────────────────────
    def _validate_parent(self):
        parents = frappe.get_all(
            "Child Parent Link", filters={"parent": self.child, "parenttype": "Child"}, pluck="parent_customer"
        )
        if not self.parent_customer and parents:
            self.parent_customer = parents[0]
        if self.parent_customer not in parents:
            frappe.throw(_("{0} is not linked as a parent of child {1}.").format(self.parent_customer, self.child))

    def _validate_plan(self):
        if not cint(self.plan.is_active) and self.docstatus == 0:
            frappe.throw(_("Subscription Plan {0} is inactive.").format(self.subscription_plan))

    def _set_dates(self):
        if not self.end_date and cint(self.plan.duration_months):
            self.end_date = add_days(add_months(self.start_date, cint(self.plan.duration_months)), -1)
        if self.end_date and getdate(self.end_date) < getdate(self.start_date):
            frappe.throw(_("End date cannot be before start date."))
        if not self.next_billing_date:
            self.next_billing_date = self.start_date

    def _validate_overlap(self):
        if self.status in ("Cancelled", "Expired"):
            return
        others = frappe.get_all(
            "Child Subscription",
            filters={
                "child": self.child,
                "name": ("!=", self.name),
                "docstatus": 1,
                "status": ("in", OPEN_STATUSES),
            },
            fields=["name", "start_date", "end_date"],
        )
        start, end = getdate(self.start_date), getdate(self.end_date) if self.end_date else None
        for o in others:
            o_start, o_end = getdate(o.start_date), getdate(o.end_date) if o.end_date else None
            if (end is None or o_start <= end) and (o_end is None or start <= o_end):
                frappe.throw(_("Child {0} already has an open subscription {1} for an overlapping period.").format(self.child, o.name))

    def _set_discount(self):
        """Apply the family (multi-child) discount on new drafts when none was entered."""
        if self.docstatus != 0 or flt(self.discount_percent):
            return
        siblings = frappe.db.count(
            "Child Subscription",
            {"parent_customer": self.parent_customer, "child": ("!=", self.child), "docstatus": 1, "status": ("in", OPEN_STATUSES)},
        )
        if not siblings:
            return
        disc = flt(self.plan.multi_child_discount_override) or flt(
            frappe.db.get_single_value("Nursery Settings", "multi_child_discount_percent")
        )
        if disc:
            self.discount_percent = disc

    def _calculate_amount(self):
        self.monthly_amount = flt(self.plan.base_price)
        self.currency = self.currency or self.plan.currency or frappe.db.get_single_value("Nursery Settings", "default_currency")
        services_total = 0
        for row in self.additional_services or []:
            row.qty = flt(row.qty) or 1
            if not flt(row.rate):
                row.rate = flt(frappe.db.get_value("Nursery Service", row.service, "price"))
            row.amount = flt(row.rate) * row.qty
            services_total += row.amount
        if not 0 <= flt(self.discount_percent) <= 100:
            frappe.throw(_("Discount must be between 0 and 100%."))
        self.final_amount = flt((self.monthly_amount + services_total) * (1 - flt(self.discount_percent) / 100), 2)

    # ── side effects ─────────────────────────────────────────────────────
    def _update_child(self):
        current = frappe.db.get_value("Child", self.child, "active_subscription")
        if self.status in OPEN_STATUSES:
            frappe.db.set_value("Child", self.child, {"active_subscription": self.name, "subscription_status": self.status})
        elif current == self.name:
            frappe.db.set_value("Child", self.child, {"active_subscription": None, "subscription_status": self.status})

    def _set_status(self, status, note=None):
        self.status = status
        if note:
            self.notes = ((self.notes or "") + f"\n{today()}: {note}").strip()
        self.save()

    # ── actions (buttons on the form) ────────────────────────────────────
    @frappe.whitelist()
    def generate_invoice(self):
        self.check_permission("write")
        from baby_care.baby_care_management.utils.billing import create_subscription_invoice

        return create_subscription_invoice(self.name)

    @frappe.whitelist()
    def suspend(self, reason=None):
        self.check_permission("write")
        if self.status not in ("Active", "Pending"):
            frappe.throw(_("Only active or pending subscriptions can be suspended."))
        self._set_status("Suspended", _("Suspended: {0}").format(reason or "-"))

    @frappe.whitelist()
    def resume(self):
        self.check_permission("write")
        if self.status != "Suspended":
            frappe.throw(_("Only suspended subscriptions can be resumed."))
        self._set_status("Active", _("Resumed"))

    @frappe.whitelist()
    def renew(self):
        """Extend the end date by one plan duration (or one billing period)."""
        self.check_permission("write")
        if self.status == "Cancelled":
            frappe.throw(_("A cancelled subscription cannot be renewed."))
        months = cint(self.plan.duration_months) or plan_period_months(self.plan)
        base = getdate(self.end_date) if self.end_date else getdate(today())
        self.end_date = add_days(add_months(add_days(base, 1), months), -1)
        if getdate(self.next_billing_date) < getdate(today()):
            self.next_billing_date = today()
        self._set_status("Active", _("Renewed until {0}").format(self.end_date))
        return self.end_date
