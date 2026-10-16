"""
Patch: create the Nursery Settings singleton if it doesn't exist,
and seed default Age Groups, Meal Categories, Attendance Statuses.
"""
import frappe


def execute():
    # Nursery Settings singleton
    if not frappe.db.exists("Nursery Settings", "Nursery Settings"):
        settings = frappe.new_doc("Nursery Settings")
        settings.facility_name = "My Nursery"
        settings.facility_type = "Nursery"
        settings.invoice_generation_day = 1
        settings.invoice_due_days = 15
        settings.allow_partial_payment = 1
        settings.auto_generate_invoices = 1
        settings.require_medical_record = 1
        settings.require_birth_certificate = 1
        settings.require_parent_id = 1
        settings.enforce_class_capacity = 1
        settings.notify_subscription_expiry_days = 14
        settings.notify_document_expiry_days = 30
        settings.notify_overdue_after_days = 7
        settings.insert(ignore_permissions=True)

    # Default age groups
    default_age_groups = [
        {"group_name": "Infants", "min_age_months": 0, "max_age_months": 12},
        {"group_name": "Toddlers", "min_age_months": 12, "max_age_months": 36},
        {"group_name": "Preschool", "min_age_months": 36, "max_age_months": 60},
        {"group_name": "Kindergarten", "min_age_months": 60, "max_age_months": 84},
    ]
    for ag in default_age_groups:
        if not frappe.db.exists("Age Group", ag["group_name"]):
            doc = frappe.new_doc("Age Group")
            doc.update(ag)
            doc.insert(ignore_permissions=True)

    # Default meal categories
    for i, cat in enumerate(["Breakfast", "Morning Snack", "Lunch", "Afternoon Snack", "Dinner"]):
        if not frappe.db.exists("Meal Category", cat):
            doc = frappe.new_doc("Meal Category")
            doc.category_name = cat
            doc.sort_order = i
            doc.insert(ignore_permissions=True)

    # Default attendance statuses
    statuses = [
        ("Present", "Present", "Green"),
        ("Absent", "Absent", "Red"),
        ("Late", "Late", "Orange"),
        ("Leave", "Leave", "Blue"),
        ("Holiday", "Holiday", "Grey"),
    ]
    for name, stype, color in statuses:
        if not frappe.db.exists("Attendance Status", name):
            doc = frappe.new_doc("Attendance Status")
            doc.status_name = name
            doc.status_type = stype
            doc.color = color
            doc.insert(ignore_permissions=True)

    # Default service categories
    for cat in ["Meals", "Transportation", "Education", "Extracurricular", "Hygiene", "Other"]:
        if not frappe.db.exists("Service Category", cat):
            doc = frappe.new_doc("Service Category")
            doc.category_name = cat
            doc.insert(ignore_permissions=True)

    frappe.db.commit()
