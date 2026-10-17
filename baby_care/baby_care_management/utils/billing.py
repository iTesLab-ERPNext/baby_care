"""
Billing: turns Child Subscriptions into ERPNext Sales Invoices.

Every invoice created here carries three custom fields (added on install):
``baby_care_subscription``, ``baby_care_child`` and ``baby_care_billing_period``.
They make duplicate-period protection reliable and let reports / dashboards
separate nursery revenue from other sales of the same company.
"""
import frappe
from frappe import _
from frappe.utils import add_days, add_months, cint, flt, getdate, today

FREQUENCY_MONTHS = {"Monthly": 1, "Quarterly": 3, "Annual": 12}


# ── public API ───────────────────────────────────────────────────────────────
def create_subscription_invoice(subscription_name, submit=None):
    """Create (and by default submit) the Sales Invoice for the subscription's next billing period."""
    sub = frappe.get_doc("Child Subscription", subscription_name)
    if sub.docstatus != 1:
        frappe.throw(_("Submit the subscription before generating invoices."))
    if sub.status == "Pending" and getdate(sub.start_date) <= getdate(today()):
        sub.db_set("status", "Active")
    if sub.status != "Active":
        frappe.throw(_("Cannot invoice a subscription with status {0}.").format(sub.status))
    if sub.end_date and getdate(sub.next_billing_date) > getdate(sub.end_date):
        frappe.throw(_("Subscription {0} has no billing period left before its end date ({1}). Renew it first.").format(sub.name, sub.end_date))

    plan = frappe.get_doc("Subscription Plan", sub.subscription_plan)
    period_start = getdate(sub.next_billing_date)
    months = period_months(plan)
    period = billing_period_label(plan, period_start)

    existing = frappe.db.get_value(
        "Sales Invoice",
        {"baby_care_subscription": sub.name, "baby_care_billing_period": period, "docstatus": ("<", 2)},
        "name",
    )
    if existing:
        frappe.throw(_("Billing period {0} is already invoiced ({1}).").format(period, existing), title=_("Duplicate invoice"))

    settings = frappe.get_single("Nursery Settings")
    company = get_company(settings)
    si = frappe.new_doc("Sales Invoice")
    si.customer = sub.parent_customer
    si.company = company
    si.posting_date = today()
    si.set_posting_time = 1
    si.due_date = add_days(today(), cint(settings.invoice_due_days) or 15)
    si.currency = sub.currency or frappe.get_cached_value("Company", company, "default_currency")
    si.baby_care_subscription = sub.name
    si.baby_care_child = sub.child
    si.baby_care_billing_period = period
    if settings.default_payment_terms:
        si.payment_terms_template = settings.default_payment_terms
    child_name = frappe.db.get_value("Child", sub.child, "full_name") or sub.child
    period_label = _("{0} to {1}").format(period_start, add_days(add_months(period_start, months), -1))

    _add_item(si, settings, _item_for_plan(plan, settings), flt(plan.base_price),
              _("{0} — {1} — {2}").format(plan.plan_name, child_name, period_label))
    for row in sub.additional_services or []:
        svc = frappe.get_cached_doc("Nursery Service", row.service)
        if svc.pricing_method == "Included in Subscription" or not flt(row.amount):
            continue
        _add_item(si, settings, _item_for_service(svc, settings), flt(row.rate), _("{0} — {1}").format(svc.service_name, child_name), qty=flt(row.qty) or 1)

    transport = _transport_line(sub.child, months)
    if transport:
        _add_item(si, settings, _item_for_name(_("Transportation"), settings), transport["rate"],
                  _("Transportation ({0}) — {1}").format(transport["route"], child_name), qty=months)

    if flt(sub.discount_percent):
        si.additional_discount_percentage = flt(sub.discount_percent)
    if plan.tax_template:
        from erpnext.controllers.accounts_controller import get_taxes_and_charges

        si.taxes_and_charges = plan.tax_template
        for tax in get_taxes_and_charges("Sales Taxes and Charges Template", plan.tax_template) or []:
            si.append("taxes", tax)

    si.flags.ignore_permissions = True
    si.insert()
    should_submit = cint(settings.auto_submit_invoices) if submit is None else cint(submit)
    if should_submit:
        si.submit()

    sub.append("invoices", {
        "sales_invoice": si.name,
        "billing_period": period,
        "amount": si.grand_total,
        "status": si.status,
        "invoice_date": si.posting_date,
    }).db_insert()
    sub.db_set({
        "next_billing_date": add_months(period_start, months),
        "last_invoice_date": today(),
    })
    return si.name


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


def get_company(settings=None):
    settings = settings or frappe.get_single("Nursery Settings")
    company = settings.default_company or frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    if not company:
        company = frappe.db.get_value("Company", {}, "name")
    if not company:
        frappe.throw(_("Set a Default Company in Nursery Settings."))
    return company


# ── items ────────────────────────────────────────────────────────────────────
def _add_item(si, settings, item_code, rate, description, qty=1):
    row = {"item_code": item_code, "qty": qty, "rate": rate, "description": description}
    if settings.default_income_account:
        row["income_account"] = settings.default_income_account
    if settings.default_cost_center:
        row["cost_center"] = settings.default_cost_center
    si.append("items", row)


def _item_group(settings):
    if settings.default_item_group:
        return settings.default_item_group
    return "Services" if frappe.db.exists("Item Group", "Services") else frappe.db.get_value("Item Group", {"is_group": 0}, "name") or "All Item Groups"


def _item_for_name(name, settings):
    code = name[:140]
    if not frappe.db.exists("Item", code):
        frappe.get_doc({
            "doctype": "Item",
            "item_code": code,
            "item_name": code,
            "item_group": _item_group(settings),
            "stock_uom": "Nos" if frappe.db.exists("UOM", "Nos") else frappe.db.get_value("UOM", {}, "name"),
            "is_stock_item": 0,
            "is_sales_item": 1,
            "include_item_in_manufacturing": 0,
        }).insert(ignore_permissions=True)
    return code


def _item_for_plan(plan, settings):
    return _item_for_name(_("Subscription: {0}").format(plan.plan_name), settings)


def _item_for_service(svc, settings):
    if svc.erpnext_item:
        return svc.erpnext_item
    code = _item_for_name(_("Service: {0}").format(svc.service_name), settings)
    frappe.db.set_value("Nursery Service", svc.name, "erpnext_item", code, update_modified=False)
    return code


def _transport_line(child, months):
    if not cint(frappe.db.get_single_value("Nursery Settings", "enable_transportation")):
        return None
    route = frappe.db.get_value("Child Transportation", {"child": child, "is_active": 1}, "route")
    if not route:
        return None
    fee = flt(frappe.db.get_value("Transportation Route", route, "monthly_fee"))
    return {"route": route, "rate": fee} if fee else None


# ── status sync ──────────────────────────────────────────────────────────────
def on_sales_invoice_change(doc, method=None):
    if not doc.get("baby_care_subscription"):
        return
    status = "Cancelled" if doc.docstatus == 2 else frappe.db.get_value("Sales Invoice", doc.name, "status")
    for row in frappe.get_all("Child Subscription Invoice", filters={"sales_invoice": doc.name}, pluck="name"):
        frappe.db.set_value("Child Subscription Invoice", row, {"status": status, "amount": doc.grand_total})


def on_payment_entry_change(doc, method=None):
    for ref in doc.get("references") or []:
        if ref.reference_doctype != "Sales Invoice":
            continue
        si = frappe.db.get_value("Sales Invoice", ref.reference_name, ["name", "status", "grand_total", "docstatus", "baby_care_subscription"], as_dict=True)
        if si and si.baby_care_subscription:
            for row in frappe.get_all("Child Subscription Invoice", filters={"sales_invoice": si.name}, pluck="name"):
                frappe.db.set_value("Child Subscription Invoice", row, "status", si.status)


# ── parent account statement ─────────────────────────────────────────────────
@frappe.whitelist()
def get_parent_statement(customer):
    """Invoices, payments, outstanding and subscriptions for one parent (Customer)."""
    frappe.has_permission("Customer", "read", customer, throw=True)
    out = {"invoices": [], "payments": [], "subscriptions": [], "children": [], "outstanding": 0, "next_due": None}
    if frappe.has_permission("Sales Invoice", "read"):
        out["invoices"] = frappe.get_list(
            "Sales Invoice",
            filters={"customer": customer, "docstatus": 1},
            fields=["name", "posting_date", "due_date", "grand_total", "outstanding_amount", "status", "baby_care_child", "baby_care_billing_period"],
            order_by="posting_date desc",
            limit_page_length=50,
        )
        out["outstanding"] = sum(flt(i.outstanding_amount) for i in out["invoices"])
        due = [i.due_date for i in out["invoices"] if flt(i.outstanding_amount) > 0 and i.due_date]
        out["next_due"] = min(due) if due else None
    if frappe.has_permission("Payment Entry", "read"):
        out["payments"] = frappe.get_list(
            "Payment Entry",
            filters={"party_type": "Customer", "party": customer, "docstatus": 1},
            fields=["name", "posting_date", "paid_amount", "mode_of_payment", "reference_no"],
            order_by="posting_date desc",
            limit_page_length=50,
        )
    if frappe.has_permission("Child Subscription", "read"):
        out["subscriptions"] = frappe.get_list(
            "Child Subscription",
            filters={"parent_customer": customer, "docstatus": ("<", 2)},
            fields=["name", "child", "subscription_plan", "status", "start_date", "end_date", "next_billing_date", "final_amount"],
            order_by="start_date desc",
        )
    if frappe.has_permission("Child", "read"):
        names = frappe.get_all("Child Parent Link", filters={"parent_customer": customer, "parenttype": "Child"}, pluck="parent")
        if names:
            out["children"] = frappe.get_list(
                "Child", filters={"name": ("in", names)}, fields=["name", "full_name", "enrollment_status", "nursery_class", "age_display"]
            )
    return out
