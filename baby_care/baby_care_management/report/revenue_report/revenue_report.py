import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
    filters = frappe._dict(filters or {})
    f = {"docstatus": 1, "baby_care_subscription": ("is", "set"), "posting_date": ("between", [filters.from_date, filters.to_date])}
    if filters.get("customer"):
        f["customer"] = filters.customer
    if filters.get("child"):
        f["baby_care_child"] = filters.child
    if filters.get("company"):
        f["company"] = filters.company
    invoices = frappe.get_list(
        "Sales Invoice",
        filters=f,
        fields=["name", "posting_date", "customer", "baby_care_child", "baby_care_subscription", "baby_care_billing_period",
                "base_grand_total", "outstanding_amount", "status", "due_date"],
        order_by="posting_date asc",
        limit_page_length=0,
    )
    plans = dict(frappe.get_all("Child Subscription", filters={"name": ("in", list({i.baby_care_subscription for i in invoices}) or [""])}, fields=["name", "subscription_plan"], as_list=True))
    for i in invoices:
        i.subscription_plan = plans.get(i.baby_care_subscription)
        i.paid = flt(i.base_grand_total) - flt(i.outstanding_amount)
    group = filters.get("group_by") or "Invoice"
    if group == "Invoice":
        return _invoice_columns(), invoices, None, _period_chart(invoices, filters), _summary(invoices)
    key = {"Month": lambda i: getdate(i.posting_date).strftime("%Y-%m"),
           "Quarter": lambda i: f"{getdate(i.posting_date).year}-Q{(getdate(i.posting_date).month - 1) // 3 + 1}",
           "Subscription Plan": lambda i: i.subscription_plan or _("(none)"),
           "Parent": lambda i: i.customer,
           "Child": lambda i: i.baby_care_child}[group]
    agg = {}
    for i in invoices:
        a = agg.setdefault(key(i), {"group": key(i), "invoices": 0, "invoiced": 0.0, "paid": 0.0, "outstanding": 0.0})
        a["invoices"] += 1
        a["invoiced"] += flt(i.base_grand_total)
        a["paid"] += flt(i.paid)
        a["outstanding"] += flt(i.outstanding_amount)
    data = list(agg.values())
    columns = [
        {"label": _(group), "fieldname": "group", "fieldtype": "Data", "width": 180},
        {"label": _("Invoices"), "fieldname": "invoices", "fieldtype": "Int", "width": 90},
        {"label": _("Invoiced"), "fieldname": "invoiced", "fieldtype": "Currency", "width": 130},
        {"label": _("Paid"), "fieldname": "paid", "fieldtype": "Currency", "width": 130},
        {"label": _("Outstanding"), "fieldname": "outstanding", "fieldtype": "Currency", "width": 130},
    ]
    chart = {"data": {"labels": [d["group"] for d in data], "datasets": [{"name": _("Invoiced"), "values": [d["invoiced"] for d in data]}, {"name": _("Paid"), "values": [d["paid"] for d in data]}]}, "type": "bar", "fieldtype": "Currency"}
    return columns, data, None, chart, _summary(invoices)


def _invoice_columns():
    return [
        {"label": _("Invoice"), "fieldname": "name", "fieldtype": "Link", "options": "Sales Invoice", "width": 150},
        {"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 95},
        {"label": _("Parent"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 160},
        {"label": _("Child"), "fieldname": "baby_care_child", "fieldtype": "Link", "options": "Child", "width": 120},
        {"label": _("Plan"), "fieldname": "subscription_plan", "fieldtype": "Link", "options": "Subscription Plan", "width": 140},
        {"label": _("Period"), "fieldname": "baby_care_billing_period", "fieldtype": "Data", "width": 90},
        {"label": _("Amount"), "fieldname": "base_grand_total", "fieldtype": "Currency", "width": 120},
        {"label": _("Paid"), "fieldname": "paid", "fieldtype": "Currency", "width": 120},
        {"label": _("Outstanding"), "fieldname": "outstanding_amount", "fieldtype": "Currency", "width": 120},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 90},
    ]


def _period_chart(invoices, filters):
    months = {}
    for i in invoices:
        m = getdate(i.posting_date).strftime("%Y-%m")
        months[m] = months.get(m, 0) + flt(i.base_grand_total)
    labels = sorted(months)
    return {"data": {"labels": labels, "datasets": [{"name": _("Revenue"), "values": [months[m] for m in labels]}]}, "type": "bar", "fieldtype": "Currency"}


def _summary(invoices):
    total = sum(flt(i.base_grand_total) for i in invoices)
    out = sum(flt(i.outstanding_amount) for i in invoices)
    return [
        {"label": _("Invoiced"), "value": total, "datatype": "Currency", "indicator": "Blue"},
        {"label": _("Collected"), "value": total - out, "datatype": "Currency", "indicator": "Green"},
        {"label": _("Outstanding"), "value": out, "datatype": "Currency", "indicator": "Red"},
    ]
