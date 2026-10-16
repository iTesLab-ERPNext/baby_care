import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}

    columns = [
        {"label": _("Child"), "fieldname": "full_name", "fieldtype": "Link",
         "options": "Child", "width": 200},
        {"label": _("Date of Birth"), "fieldname": "date_of_birth", "fieldtype": "Date", "width": 110},
        {"label": _("Age"), "fieldname": "age_display", "fieldtype": "Data", "width": 80},
        {"label": _("Gender"), "fieldname": "gender", "fieldtype": "Data", "width": 80},
        {"label": _("Class"), "fieldname": "nursery_class", "fieldtype": "Link",
         "options": "Nursery Class", "width": 140},
        {"label": _("Teacher"), "fieldname": "assigned_teacher", "fieldtype": "Link",
         "options": "Teacher Profile", "width": 140},
        {"label": _("Status"), "fieldname": "enrollment_status", "fieldtype": "Data", "width": 100},
        {"label": _("Parent"), "fieldname": "parent_customer", "fieldtype": "Link",
         "options": "Customer", "width": 180},
        {"label": _("Subscription"), "fieldname": "subscription_status",
         "fieldtype": "Data", "width": 110},
        {"label": _("Registration Date"), "fieldname": "registration_date",
         "fieldtype": "Date", "width": 120},
    ]

    conditions = "1=1"
    if filters.get("enrollment_status"):
        conditions += f" AND c.enrollment_status = {frappe.db.escape(filters['enrollment_status'])}"
    if filters.get("nursery_class"):
        conditions += f" AND c.nursery_class = {frappe.db.escape(filters['nursery_class'])}"
    if filters.get("assigned_teacher"):
        conditions += f" AND c.assigned_teacher = {frappe.db.escape(filters['assigned_teacher'])}"

    data = frappe.db.sql(f"""
        SELECT
            c.name AS full_name,
            c.date_of_birth,
            c.age_display,
            c.gender,
            c.nursery_class,
            c.assigned_teacher,
            c.enrollment_status,
            c.subscription_status,
            c.registration_date,
            cpl.parent_customer
        FROM `tabChild` c
        LEFT JOIN `tabChild Parent Link` cpl
            ON cpl.parent = c.name AND cpl.is_primary = 1
        WHERE {conditions}
        ORDER BY c.full_name
    """, as_dict=True)

    return columns, data
