import frappe
from frappe import _
from frappe.utils import getdate, today

from baby_care.baby_care_management.doctype.child.child import age_in_months


def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = [
        {"label": _("Child"), "fieldname": "name", "fieldtype": "Link", "options": "Child", "width": 120},
        {"label": _("Full Name"), "fieldname": "full_name", "fieldtype": "Data", "width": 180},
        {"label": _("Age (months)"), "fieldname": "age_months", "fieldtype": "Int", "width": 100},
        {"label": _("Gender"), "fieldname": "gender", "fieldtype": "Data", "width": 80},
        {"label": _("Class"), "fieldname": "nursery_class", "fieldtype": "Link", "options": "Nursery Class", "width": 140},
        {"label": _("Age Group"), "fieldname": "age_group", "fieldtype": "Link", "options": "Age Group", "width": 110},
        {"label": _("Teacher"), "fieldname": "assigned_teacher", "fieldtype": "Link", "options": "Teacher Profile", "width": 150},
        {"label": _("Status"), "fieldname": "enrollment_status", "fieldtype": "Data", "width": 90},
        {"label": _("Registered"), "fieldname": "registration_date", "fieldtype": "Date", "width": 100},
        {"label": _("Next Birthday"), "fieldname": "next_birthday", "fieldtype": "Date", "width": 110},
        {"label": _("Allergies"), "fieldname": "has_allergies", "fieldtype": "Check", "width": 80},
    ]
    f = {}
    for key in ("enrollment_status", "nursery_class", "assigned_teacher", "age_group", "gender"):
        if filters.get(key):
            f[key] = filters[key]
    rows = frappe.get_list(
        "Child",
        filters=f,
        fields=["name", "full_name", "date_of_birth", "gender", "nursery_class", "age_group", "assigned_teacher",
                "enrollment_status", "registration_date", "has_allergies"],
        order_by="full_name asc",
        limit_page_length=0,
    )
    t = getdate(today())
    for r in rows:
        if r.date_of_birth:
            r.age_months = age_in_months(r.date_of_birth)
            dob = getdate(r.date_of_birth)
            try:
                b = dob.replace(year=t.year)
            except ValueError:
                b = dob.replace(year=t.year, day=28)
            r.next_birthday = b if b >= t else b.replace(year=t.year + 1)
    if filters.get("parent_customer"):
        allowed = set(frappe.get_all("Child Parent Link", filters={"parent_customer": filters.parent_customer, "parenttype": "Child"}, pluck="parent"))
        rows = [r for r in rows if r.name in allowed]

    by_class = {}
    for r in rows:
        by_class[r.nursery_class or _("Unassigned")] = by_class.get(r.nursery_class or _("Unassigned"), 0) + 1
    chart = {"data": {"labels": list(by_class), "datasets": [{"name": _("Children"), "values": list(by_class.values())}]}, "type": "bar"}
    summary = [
        {"label": _("Children"), "value": len(rows), "indicator": "Blue"},
        {"label": _("Active"), "value": len([r for r in rows if r.enrollment_status == "Active"]), "indicator": "Green"},
        {"label": _("With allergies"), "value": len([r for r in rows if r.has_allergies]), "indicator": "Red"},
    ]
    return columns, rows, None, chart, summary
