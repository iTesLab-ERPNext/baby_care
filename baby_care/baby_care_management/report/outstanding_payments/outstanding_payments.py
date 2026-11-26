import frappe
from frappe import _
from frappe.utils import date_diff, flt, today


def execute(filters=None):
    filters = frappe._dict(filters or {})
    f = {"docstatus": 1, "outstanding_amount": (">", 0)}
    if filters.get("parent_profile"):
        f["parent_profile"] = filters.parent_profile
    if filters.get("overdue_only"):
        f["due_date"] = ("<", today())
    rows = frappe.get_list(
        "Nursery Invoice",
        filters=f,
        fields=["name", "parent_profile", "parent_name", "child", "billing_period", "posting_date", "due_date", "grand_total", "outstanding_amount", "status"],
        order_by="due_date asc",
        limit_page_length=0,
    )
    buckets = {"0-30": 0.0, "31-60": 0.0, "61-90": 0.0, "90+": 0.0, _("Not due"): 0.0}
    for r in rows:
        r.days_overdue = max(date_diff(today(), r.due_date), 0) if r.due_date else 0
        d = r.days_overdue
        b = _("Not due") if d == 0 else "0-30" if d <= 30 else "31-60" if d <= 60 else "61-90" if d <= 90 else "90+"
        r.ageing = b
        buckets[b] += flt(r.outstanding_amount)
    columns = [
        {"label": _("Invoice"), "fieldname": "name", "fieldtype": "Link", "options": "Nursery Invoice", "width": 150},
        {"label": _("Parent"), "fieldname": "parent_profile", "fieldtype": "Link", "options": "Parent Profile", "width": 110},
        {"label": _("Parent Name"), "fieldname": "parent_name", "fieldtype": "Data", "width": 160},
        {"label": _("Child"), "fieldname": "child", "fieldtype": "Link", "options": "Child", "width": 120},
        {"label": _("Period"), "fieldname": "billing_period", "fieldtype": "Data", "width": 90},
        {"label": _("Invoice Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
        {"label": _("Due Date"), "fieldname": "due_date", "fieldtype": "Date", "width": 100},
        {"label": _("Amount"), "fieldname": "grand_total", "fieldtype": "Currency", "width": 120},
        {"label": _("Outstanding"), "fieldname": "outstanding_amount", "fieldtype": "Currency", "width": 120},
        {"label": _("Days Overdue"), "fieldname": "days_overdue", "fieldtype": "Int", "width": 100},
        {"label": _("Ageing"), "fieldname": "ageing", "fieldtype": "Data", "width": 80},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 90},
    ]
    chart = {"data": {"labels": list(buckets), "datasets": [{"name": _("Outstanding"), "values": list(buckets.values())}]}, "type": "bar", "fieldtype": "Currency"}
    summary = [
        {"label": _("Outstanding"), "value": sum(flt(r.outstanding_amount) for r in rows), "datatype": "Currency", "indicator": "Red"},
        {"label": _("Overdue invoices"), "value": len([r for r in rows if r.days_overdue]), "indicator": "Orange"},
        {"label": _("Parents concerned"), "value": len({r.parent_profile for r in rows}), "indicator": "Blue"},
    ]
    return columns, rows, None, chart, summary
