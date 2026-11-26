"""
Billing: Child Subscriptions → Nursery Invoices, Nursery Payments → invoice balances.

Everything lives in the app's own DocTypes (no ERPNext):

* ``Nursery Invoice`` (submittable) — one per child and billing period, with
  lines, discount, tax, paid and outstanding amounts and a status.
* ``Nursery Payment`` (submittable) — money received from a parent, allocated
  to one or more invoices (oldest first when left empty). Anything not
  allocated stays as a credit on the parent.
"""
import frappe
from frappe import _
from frappe.utils import add_days, add_months, cint, flt, getdate, today

FREQUENCY_MONTHS = {"Monthly": 1, "Quarterly": 3, "Annual": 12}
OPEN = ("Unpaid", "Partly Paid", "Overdue")


def settings():
    return frappe.get_cached_doc("Nursery Settings")


def default_currency():
    return frappe.db.get_single_value("Nursery Settings", "default_currency") or frappe.db.get_default("currency") or "TND"


# ── subscription invoices ────────────────────────────────────────────────────
def create_subscription_invoice(subscription_name, submit=None):
    """Create (and by default submit) the invoice for the subscription's next billing period."""
    sub = frappe.get_doc("Child Subscription", subscription_name)
    if sub.docstatus != 1:
        frappe.throw(_("Submit the subscription before generating invoices."))
    if sub.status == "Pending" and getdate(sub.start_date) <= getdate(today()):
        sub.db_set("status", "Active")
    if sub.status != "Active":
        frappe.throw(_("Cannot invoice a subscription with status {0}.").format(sub.status))
    if not sub.parent_profile:
        frappe.throw(_("Subscription {0} has no parent to invoice. Set the Parent on the subscription first.").format(sub.name))
    if sub.end_date and getdate(sub.next_billing_date) > getdate(sub.end_date):
        frappe.throw(_("Subscription {0} has no billing period left before its end date ({1}). Renew it first.").format(sub.name, sub.end_date))

    plan = frappe.get_doc("Subscription Plan", sub.subscription_plan)
    period_start = getdate(sub.next_billing_date)
    months = period_months(plan)
    period = billing_period_label(plan, period_start)

    existing = frappe.db.get_value(
        "Nursery Invoice", {"child_subscription": sub.name, "billing_period": period, "docstatus": ("<", 2)}, "name"
    )
    if existing:
        frappe.throw(_("Billing period {0} is already invoiced ({1}).").format(period, existing), title=_("Duplicate invoice"))

    s = frappe.get_single("Nursery Settings")
    inv = frappe.new_doc("Nursery Invoice")
    inv.parent_profile = sub.parent_profile
    inv.child = sub.child
    inv.child_subscription = sub.name
    inv.billing_period = period
    inv.posting_date = today()
    inv.due_date = add_days(today(), cint(s.invoice_due_days) or 15)
    inv.currency = sub.currency or plan.currency or default_currency()
    inv.discount_percent = flt(sub.discount_percent)
    inv.tax_rate = flt(plan.tax_rate) if plan.tax_rate is not None and flt(plan.tax_rate) else flt(s.default_tax_rate)

    child_name = frappe.db.get_value("Child", sub.child, "full_name") or sub.child
    period_label = _("{0} to {1}").format(
        frappe.format(period_start, "Date"), frappe.format(add_days(add_months(period_start, months), -1), "Date")
    )
    inv.append("items", {"description": _("{0} — {1} — {2}").format(plan.plan_name, child_name, period_label),
                         "qty": 1, "rate": flt(plan.base_price)})
    for row in sub.additional_services or []:
        svc = frappe.get_cached_doc("Nursery Service", row.service)
        if svc.pricing_method == "Included in Subscription" or not flt(row.amount):
            continue
        inv.append("items", {"description": _("{0} — {1}").format(svc.service_name, child_name), "service": svc.name,
                             "qty": flt(row.qty) or 1, "rate": flt(row.rate)})
    transport = _transport_line(sub.child)
    if transport:
        inv.append("items", {"description": _("Transportation ({0}) — {1}").format(transport["route"], child_name),
                             "qty": months, "rate": transport["rate"]})

    inv.flags.ignore_permissions = True
    inv.insert()
    if cint(s.auto_submit_invoices) if submit is None else cint(submit):
        inv.submit()

    sub.append("invoices", {
        "invoice": inv.name, "billing_period": period, "amount": inv.grand_total,
        "status": inv.status, "invoice_date": inv.posting_date,
    }).db_insert()
    sub.db_set({"next_billing_date": add_months(period_start, months), "last_invoice_date": today()})
    return inv.name


def period_months(plan):
    return FREQUENCY_MONTHS.get(plan.billing_frequency) or max(cint(plan.duration_months), 1)


def billing_period_label(plan, start):
    start = getdate(start)
    if plan.billing_frequency == "Quarterly":
        return f"{start.year}-Q{(start.month - 1) // 3 + 1}"
    if plan.billing_frequency == "Annual":
        return str(start.year)
    if plan.billing_frequency == "Custom" and period_months(plan) > 1:
        return f"{start.strftime('%Y-%m')}+{period_months(plan)}M"
    return start.strftime("%Y-%m")


def _transport_line(child):
    if not cint(frappe.db.get_single_value("Nursery Settings", "enable_transportation")):
        return None
    route = frappe.db.get_value("Child Transportation", {"child": child, "is_active": 1}, "route")
    if not route:
        return None
    fee = flt(frappe.db.get_value("Transportation Route", route, "monthly_fee"))
    return {"route": route, "rate": fee} if fee else None


# ── balances ─────────────────────────────────────────────────────────────────
def invoice_status(grand_total, outstanding, due_date, docstatus=1):
    if docstatus == 0:
        return "Draft"
    if docstatus == 2:
        return "Cancelled"
    if flt(outstanding, 2) <= 0:
        return "Paid"
    if due_date and getdate(due_date) < getdate(today()):
        return "Overdue"
    if flt(outstanding, 2) < flt(grand_total, 2):
        return "Partly Paid"
    return "Unpaid"


def paid_on_invoice(invoice, exclude_payment=None):
    """Sum allocated to an invoice by submitted payments."""
    cond, args = "", {"inv": invoice}
    if exclude_payment:
        cond, args["ex"] = " and p.name != %(ex)s", exclude_payment
    return flt(frappe.db.sql(
        f"""select coalesce(sum(a.allocated_amount), 0) from `tabNursery Payment Allocation` a
            join `tabNursery Payment` p on p.name = a.parent
            where a.parenttype = 'Nursery Payment' and a.invoice = %(inv)s and p.docstatus = 1{cond}""",
        args,
    )[0][0])


def update_invoice_balance(invoice):
    """Recompute paid / outstanding / status of a submitted invoice from its payments."""
    inv = frappe.db.get_value("Nursery Invoice", invoice, ["name", "grand_total", "due_date", "docstatus", "status"], as_dict=True)
    if not inv or inv.docstatus != 1:
        return
    paid = paid_on_invoice(invoice)
    outstanding = flt(flt(inv.grand_total) - paid, 2)
    status = invoice_status(inv.grand_total, outstanding, inv.due_date)
    frappe.db.set_value("Nursery Invoice", invoice, {"paid_amount": paid, "outstanding_amount": outstanding, "status": status},
                        update_modified=False)
    sync_subscription_row(invoice, status)


def sync_subscription_row(invoice, status=None, amount=None):
    for row in frappe.get_all("Child Subscription Invoice", filters={"invoice": invoice}, pluck="name"):
        values = {"status": status or frappe.db.get_value("Nursery Invoice", invoice, "status")}
        if amount is not None:
            values["amount"] = amount
        frappe.db.set_value("Child Subscription Invoice", row, values, update_modified=False)


def refresh_overdue():
    """Daily: unpaid invoices past their due date become Overdue."""
    for name in frappe.get_all("Nursery Invoice", filters={"docstatus": 1, "status": ("in", ("Unpaid", "Partly Paid")),
                                                          "due_date": ("<", today())}, pluck="name"):
        update_invoice_balance(name)


def open_invoices(parent_profile, exclude_payment=None):
    """Submitted invoices of a parent with something left to pay, oldest first."""
    rows = frappe.get_all("Nursery Invoice", filters={"parent_profile": parent_profile, "docstatus": 1, "outstanding_amount": (">", 0)},
                          fields=["name", "child", "grand_total", "outstanding_amount", "due_date", "posting_date"],
                          order_by="due_date asc, posting_date asc, name asc")
    if exclude_payment:  # outstanding as if this payment did not exist yet
        for r in rows:
            r.outstanding_amount = flt(r.grand_total) - paid_on_invoice(r.name, exclude_payment)
    return rows


def parent_credit(parent_profile):
    return flt(frappe.db.sql("""select coalesce(sum(unallocated_amount), 0) from `tabNursery Payment`
                                where parent_profile = %s and docstatus = 1""", parent_profile)[0][0])


# ── parent account statement ─────────────────────────────────────────────────
@frappe.whitelist()
def get_parent_statement(parent_profile):
    """Invoices, payments, outstanding and subscriptions for one parent."""
    frappe.has_permission("Parent Profile", "read", parent_profile, throw=True)
    out = {"invoices": [], "payments": [], "subscriptions": [], "children": [], "outstanding": 0, "credit": 0, "next_due": None}
    if frappe.has_permission("Nursery Invoice", "read"):
        out["invoices"] = frappe.get_list(
            "Nursery Invoice", filters={"parent_profile": parent_profile, "docstatus": 1},
            fields=["name", "posting_date", "due_date", "grand_total", "outstanding_amount", "status", "child", "billing_period", "currency"],
            order_by="posting_date desc", limit_page_length=0,
        )
        out["outstanding"] = sum(flt(i.outstanding_amount) for i in out["invoices"])
        due = [i.due_date for i in out["invoices"] if flt(i.outstanding_amount) > 0 and i.due_date]
        out["next_due"] = min(due) if due else None
    if frappe.has_permission("Nursery Payment", "read"):
        out["payments"] = frappe.get_list(
            "Nursery Payment", filters={"parent_profile": parent_profile, "docstatus": 1},
            fields=["name", "payment_date", "amount", "mode_of_payment", "reference_no", "unallocated_amount"],
            order_by="payment_date desc", limit_page_length=0,
        )
        out["credit"] = sum(flt(p.unallocated_amount) for p in out["payments"])
    if frappe.has_permission("Child Subscription", "read"):
        out["subscriptions"] = frappe.get_list(
            "Child Subscription", filters={"parent_profile": parent_profile, "docstatus": ("<", 2)},
            fields=["name", "child", "subscription_plan", "status", "start_date", "end_date", "next_billing_date", "final_amount"],
            order_by="start_date desc",
        )
    if frappe.has_permission("Child", "read"):
        names = frappe.get_all("Child Parent Link", filters={"parent_profile": parent_profile, "parenttype": "Child"}, pluck="parent")
        if names:
            out["children"] = frappe.get_list(
                "Child", filters={"name": ("in", names)}, fields=["name", "full_name", "enrollment_status", "nursery_class", "age_display"]
            )
    return out
