import frappe
from frappe import _
from frappe.utils import add_days, today


def execute(filters=None):
    filters = frappe._dict(filters or {})
    days = int(filters.get("within_days") or frappe.db.get_single_value("Nursery Settings", "notify_document_expiry_days") or 30)
    visible = {c.name: c.full_name for c in frappe.get_list("Child", filters={"enrollment_status": "Active"}, fields=["name", "full_name"], limit_page_length=0)}
    rows = []

    if frappe.has_permission("Child Document", "read"):
        from baby_care.baby_care_management.doctype.child_document.child_document import get_missing_mandatory_documents

        for child, doc_type in get_missing_mandatory_documents():
            if child in visible:
                rows.append({"alert": _("Missing document"), "severity": "High", "child": child, "child_name": visible[child], "detail": doc_type})
        for d in frappe.get_list("Child Document", filters={"status": ("in", ["Expired", "Missing"])}, fields=["name", "child", "parent_customer", "document_type", "expiry_date", "status"], limit_page_length=0):
            rows.append({"alert": _("Document {0}").format(d.status.lower()), "severity": "High", "child": d.child, "child_name": visible.get(d.child), "parent_customer": d.parent_customer,
                         "detail": d.document_type, "date": d.expiry_date, "reference": d.name})
        for d in frappe.get_list("Child Document", filters={"status": "Valid", "expiry_date": ("between", [today(), add_days(today(), days)])}, fields=["name", "child", "parent_customer", "document_type", "expiry_date"], limit_page_length=0):
            rows.append({"alert": _("Document expiring"), "severity": "Medium", "child": d.child, "child_name": visible.get(d.child), "parent_customer": d.parent_customer,
                         "detail": d.document_type, "date": d.expiry_date, "reference": d.name})

    if frappe.has_permission("Medical Record", "read"):
        for m in frappe.get_list("Medical Record", fields=["name", "child"], limit_page_length=0):
            for a in frappe.get_all("Child Allergy", filters={"parent": m.name, "severity": ("in", ["Severe", "Life-Threatening"])}, fields=["allergen", "severity", "treatment"]):
                rows.append({"alert": _("Severe allergy"), "severity": "High", "child": m.child, "child_name": visible.get(m.child), "detail": f"{a.allergen} ({a.severity}) — {a.treatment or ''}", "reference": m.name})
            for v in frappe.get_all("Child Vaccination", filters={"parent": m.name, "next_due": ("<=", add_days(today(), days))}, fields=["vaccine_name", "next_due"]):
                rows.append({"alert": _("Vaccination due"), "severity": "Medium", "child": m.child, "child_name": visible.get(m.child), "detail": v.vaccine_name, "date": v.next_due, "reference": m.name})
        with_record = set(frappe.get_all("Medical Record", pluck="child"))
        if frappe.db.get_single_value("Nursery Settings", "require_medical_record"):
            for child, name in visible.items():
                if child not in with_record:
                    rows.append({"alert": _("No medical record"), "severity": "Medium", "child": child, "child_name": name, "detail": _("Medical record required by settings")})

    if filters.get("severity"):
        rows = [r for r in rows if r["severity"] == filters.severity]
    columns = [
        {"label": _("Alert"), "fieldname": "alert", "fieldtype": "Data", "width": 160},
        {"label": _("Severity"), "fieldname": "severity", "fieldtype": "Data", "width": 80},
        {"label": _("Child"), "fieldname": "child", "fieldtype": "Link", "options": "Child", "width": 120},
        {"label": _("Name"), "fieldname": "child_name", "fieldtype": "Data", "width": 170},
        {"label": _("Parent"), "fieldname": "parent_customer", "fieldtype": "Link", "options": "Customer", "width": 150},
        {"label": _("Detail"), "fieldname": "detail", "fieldtype": "Data", "width": 240},
        {"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 100},
        {"label": _("Reference"), "fieldname": "reference", "fieldtype": "Data", "width": 140},
    ]
    return columns, rows
