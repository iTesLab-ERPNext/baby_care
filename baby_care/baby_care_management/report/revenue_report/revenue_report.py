import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}

    columns = [
        {"label": _("Invoice"), "fieldname": "name", "fieldtype": "Link",
         "options": "Sales Invoice", "width": 150},
        {"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
        {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link",
         "options": "Customer", "width": 180},
        {"label": _("Amount"), "fieldname": "grand_total", "fieldtype": "Currency", "width": 120},
        {"label": _("Outstanding"), "fieldname": "outstanding_amount",
         "fieldtype": "Currency", "width": 120},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 90},
        {"label": _("Due Date"), "fieldname": "due_date", "fieldtype": "Date", "width": 100},
    ]

    cond = "docstatus = 1"
    if filters.get("from_date"):
        cond += f" AND posting_date >= {frappe.db.escape(filters['from_date'])}"
    if filters.get("to_date"):
        cond += f" AND posting_date <= {frappe.db.escape(filters['to_date'])}"

    data = frappe.db.sql(f"""
        SELECT name, posting_date, customer, grand_total, outstanding_amount, status, due_date
        FROM `tabSales Invoice`
        WHERE {cond}
        ORDER BY posting_date DESC
    """, as_dict=True)

    return columns, data
