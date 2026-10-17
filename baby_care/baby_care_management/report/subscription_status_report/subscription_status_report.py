import frappe
from frappe import _
from frappe.utils import add_days, getdate, today


def execute(filters=None):
    filters = frappe._dict(filters or {})
    f = {"docstatus": ("<", 2)}
    for key in ("status", "subscription_plan", "parent_customer", "child"):
        if filters.get(key):
            f[key] = filters[key]
    if filters.get("expiring_within_days"):
        f["end_date"] = ("between", [today(), add_days(today(), int(filters.expiring_within_days))])
    rows = frappe.get_list(
        "Child Subscription",
        filters=f,
        fields=["name", "child", "parent_customer", "subscription_plan", "status", "start_date", "end_date",
                "next_billing_date", "last_invoice_date", "discount_percent", "final_amount", "currency"],
        order_by="end_date asc",
        limit_page_length=0,
    )
    t = getdate(today())
    for r in rows:
        r.days_left = (getdate(r.end_date) - t).days if r.end_date else None
    columns = [
        {"label": _("Subscription"), "fieldname": "name", "fieldtype": "Link", "options": "Child Subscription", "width": 170},
        {"label": _("Child"), "fieldname": "child", "fieldtype": "Link", "options": "Child", "width": 120},
        {"label": _("Parent"), "fieldname": "parent_customer", "fieldtype": "Link", "options": "Customer", "width": 160},
        {"label": _("Plan"), "fieldname": "subscription_plan", "fieldtype": "Link", "options": "Subscription Plan", "width": 140},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 90},
        {"label": _("Start"), "fieldname": "start_date", "fieldtype": "Date", "width": 95},
        {"label": _("End"), "fieldname": "end_date", "fieldtype": "Date", "width": 95},
        {"label": _("Days Left"), "fieldname": "days_left", "fieldtype": "Int", "width": 80},
        {"label": _("Next Billing"), "fieldname": "next_billing_date", "fieldtype": "Date", "width": 100},
        {"label": _("Discount %"), "fieldname": "discount_percent", "fieldtype": "Percent", "width": 90},
        {"label": _("Amount / Period"), "fieldname": "final_amount", "fieldtype": "Currency", "options": "currency", "width": 120},
    ]
    status_count = {}
    for r in rows:
        status_count[r.status] = status_count.get(r.status, 0) + 1
    chart = {"data": {"labels": list(status_count), "datasets": [{"values": list(status_count.values())}]}, "type": "pie"}
    return columns, rows, None, chart
