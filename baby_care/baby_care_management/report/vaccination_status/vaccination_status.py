import frappe
from frappe import _
from frappe.utils import getdate, today


def execute(filters=None):
    filters = frappe._dict(filters or {})
    records = frappe.get_list("Medical Record", fields=["name", "child"], filters={"child": filters.child} if filters.get("child") else {}, limit_page_length=0)
    names = dict(frappe.get_all("Child", filters={"name": ("in", [r.child for r in records] or [""])}, fields=["name", "full_name"], as_list=True))
    rows = []
    t = getdate(today())
    for rec in records:
        for v in frappe.get_all("Child Vaccination", filters={"parent": rec.name, "parenttype": "Medical Record"}, fields=["vaccine_name", "dose", "date_given", "next_due", "notes"], order_by="date_given asc"):
            status = _("Up to date")
            if v.next_due and getdate(v.next_due) < t:
                status = _("Overdue")
            elif v.next_due and (getdate(v.next_due) - t).days <= 30:
                status = _("Due soon")
            if filters.get("only_due") and status == _("Up to date"):
                continue
            rows.append(dict(v, child=rec.child, child_name=names.get(rec.child), medical_record=rec.name, status=status))
    columns = [
        {"label": _("Child"), "fieldname": "child", "fieldtype": "Link", "options": "Child", "width": 120},
        {"label": _("Name"), "fieldname": "child_name", "fieldtype": "Data", "width": 170},
        {"label": _("Vaccine"), "fieldname": "vaccine_name", "fieldtype": "Data", "width": 150},
        {"label": _("Dose"), "fieldname": "dose", "fieldtype": "Data", "width": 70},
        {"label": _("Given"), "fieldname": "date_given", "fieldtype": "Date", "width": 100},
        {"label": _("Next Due"), "fieldname": "next_due", "fieldtype": "Date", "width": 100},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
        {"label": _("Medical Record"), "fieldname": "medical_record", "fieldtype": "Link", "options": "Medical Record", "width": 160},
    ]
    return columns, rows
