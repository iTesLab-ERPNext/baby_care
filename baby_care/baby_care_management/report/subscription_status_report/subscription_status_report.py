import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}

    columns = [
        {"label": _("Subscription"), "fieldname": "name", "fieldtype": "Link",
         "options": "Child Subscription", "width": 160},
        {"label": _("Child"), "fieldname": "child", "fieldtype": "Link",
         "options": "Child", "width": 180},
        {"label": _("Parent"), "fieldname": "parent_customer", "fieldtype": "Link",
         "options": "Customer", "width": 180},
        {"label": _("Plan"), "fieldname": "subscription_plan", "fieldtype": "Link",
         "options": "Subscription Plan", "width": 150},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 90},
        {"label": _("Start"), "fieldname": "start_date", "fieldtype": "Date", "width": 100},
        {"label": _("End"), "fieldname": "end_date", "fieldtype": "Date", "width": 100},
        {"label": _("Next Billing"), "fieldname": "next_billing_date",
         "fieldtype": "Date", "width": 110},
        {"label": _("Amount"), "fieldname": "final_amount", "fieldtype": "Currency", "width": 110},
    ]

    conditions = "1=1"
    if filters.get("status"):
        conditions += f" AND status = {frappe.db.escape(filters['status'])}"

    data = frappe.db.sql(f"""
        SELECT name, child, parent_customer, subscription_plan,
               status, start_date, end_date, next_billing_date, final_amount
        FROM `tabChild Subscription`
        WHERE docstatus = 1 AND {conditions}
        ORDER BY next_billing_date ASC
    """, as_dict=True)

    return columns, data
