import frappe
from frappe import _
from frappe.utils import today


def execute(filters=None):
    filters = filters or {}
    date = filters.get("attendance_date") or today()

    columns = [
        {"label": _("Child"), "fieldname": "child", "fieldtype": "Link",
         "options": "Child", "width": 180},
        {"label": _("Class"), "fieldname": "nursery_class", "fieldtype": "Link",
         "options": "Nursery Class", "width": 140},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
        {"label": _("Check-In"), "fieldname": "check_in_time", "fieldtype": "Time", "width": 90},
        {"label": _("Check-Out"), "fieldname": "check_out_time", "fieldtype": "Time", "width": 90},
        {"label": _("Picked Up By"), "fieldname": "pickup_person", "fieldtype": "Data", "width": 140},
        {"label": _("Notes"), "fieldname": "notes", "fieldtype": "Data", "width": 200},
    ]

    cond = f"a.attendance_date = {frappe.db.escape(date)}"
    if filters.get("nursery_class"):
        cond += f" AND a.nursery_class = {frappe.db.escape(filters['nursery_class'])}"

    data = frappe.db.sql(f"""
        SELECT a.child, a.nursery_class, astatus.status_name AS status,
               a.check_in_time, a.check_out_time, a.pickup_person, a.notes
        FROM `tabChild Attendance` a
        LEFT JOIN `tabAttendance Status` astatus ON astatus.name = a.status
        WHERE {cond}
        ORDER BY a.child
    """, as_dict=True)

    return columns, data
