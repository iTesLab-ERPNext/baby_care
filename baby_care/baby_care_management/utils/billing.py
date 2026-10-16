"""
baby_care.baby_care_management.utils.billing
Billing utilities — invoice generation and payment hooks.
"""
import frappe
from frappe import _
from frappe.utils import today, getdate, add_months, flt, nowdate


def create_subscription_invoice(subscription_name):
    """Create a Sales Invoice for one subscription billing period."""
    sub = frappe.get_doc("Child Subscription", subscription_name)

    if sub.docstatus != 1:
        frappe.throw(_("Subscription must be submitted before generating an invoice."))

    if sub.status not in ("Active", "Pending"):
        frappe.throw(_("Cannot invoice a subscription with status: {0}").format(sub.status))

    billing_period = _billing_period_label(sub)

    # Prevent duplicate invoice for the same period
    existing = frappe.db.exists(
        "Child Subscription Invoice",
        {"parent": subscription_name, "billing_period": billing_period},
    )
    if existing:
        frappe.throw(
            _("Invoice for billing period {0} already exists.").format(billing_period)
        )

    settings = frappe.get_single("Nursery Settings")
    plan = frappe.get_doc("Subscription Plan", sub.subscription_plan)

    # Build Sales Invoice
    si = frappe.new_doc("Sales Invoice")
    si.customer = sub.parent_customer
    si.company = settings.default_company
    si.posting_date = today()
    si.due_date = _due_date(settings)
    si.currency = sub.currency or "TND"

    if settings.default_income_account:
        si.income_account = settings.default_income_account
    if settings.default_cost_center:
        si.cost_center = settings.default_cost_center
    if plan.tax_template:
        si.taxes_and_charges = plan.tax_template

    # Line item — use ERPNext Item or a generic item
    item_code = _get_or_create_item(plan, sub)
    si.append("items", {
        "item_code": item_code,
        "qty": 1,
        "rate": flt(sub.final_amount),
        "description": _("Subscription: {0} — {1} — Period: {2}").format(
            plan.plan_name, sub.child, billing_period
        ),
    })

    si.insert(ignore_permissions=True)
    si.submit()

    # Record on subscription
    frappe.get_doc("Child Subscription", subscription_name).append(
        "invoices",
        {
            "sales_invoice": si.name,
            "billing_period": billing_period,
            "amount": si.grand_total,
            "status": "Unpaid",
            "invoice_date": today(),
        },
    ).save(ignore_permissions=True)

    # Advance next billing date
    _advance_next_billing(subscription_name, sub, plan)

    frappe.db.commit()
    return si.name


def _billing_period_label(sub):
    plan = frappe.get_doc("Subscription Plan", sub.subscription_plan)
    billing_date = getdate(sub.next_billing_date or today())
    if plan.billing_frequency in ("Monthly", "Custom"):
        return billing_date.strftime("%Y-%m")
    elif plan.billing_frequency == "Quarterly":
        q = (billing_date.month - 1) // 3 + 1
        return f"{billing_date.year}-Q{q}"
    elif plan.billing_frequency == "Annual":
        return str(billing_date.year)
    return billing_date.strftime("%Y-%m")


def _due_date(settings):
    from frappe.utils import add_days
    days = int(settings.invoice_due_days or 15)
    return add_days(today(), days)


def _get_or_create_item(plan, sub):
    """Return ERPNext Item code for the subscription plan, creating if needed."""
    item_name = f"Subscription: {plan.plan_name}"
    if frappe.db.exists("Item", item_name):
        return item_name
    item = frappe.new_doc("Item")
    item.item_code = item_name
    item.item_name = item_name
    item.item_group = "Services"
    item.stock_uom = "Nos"
    item.is_stock_item = 0
    item.is_sales_item = 1
    item.description = plan.description or plan.plan_name
    item.insert(ignore_permissions=True)
    return item.item_code


def _advance_next_billing(subscription_name, sub, plan):
    freq = plan.billing_frequency
    if freq == "Monthly":
        months = 1
    elif freq == "Quarterly":
        months = 3
    elif freq == "Annual":
        months = 12
    else:
        months = int(plan.duration_months or 1)
    next_date = add_months(getdate(sub.next_billing_date or today()), months)
    frappe.db.set_value("Child Subscription", subscription_name, {
        "next_billing_date": next_date,
        "last_invoice_date": today(),
    })


# ── Doc event hooks ─────────────────────────────────────────────────────────
def on_sales_invoice_submit(doc, method):
    """Update subscription invoice status when SI is submitted."""
    _update_sub_invoice_status(doc, "Unpaid")


def on_sales_invoice_cancel(doc, method):
    """Update subscription invoice status when SI is cancelled."""
    _update_sub_invoice_status(doc, "Cancelled")


def _update_sub_invoice_status(si_doc, status):
    rows = frappe.db.get_all(
        "Child Subscription Invoice",
        filters={"sales_invoice": si_doc.name},
        fields=["name", "parent"],
    )
    for row in rows:
        frappe.db.set_value("Child Subscription Invoice", row.name, "status", status)
