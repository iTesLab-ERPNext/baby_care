frappe.query_reports["Enrolled Children Summary"] = {
    "filters": [
        {
            "fieldname": "enrollment_status",
            "label": __("Enrollment Status"),
            "fieldtype": "Select",
            "options": "\nPending\nActive\nSuspended\nWithdrawn\nGraduated",
            "default": "Active"
        },
        {
            "fieldname": "nursery_class",
            "label": __("Class"),
            "fieldtype": "Link",
            "options": "Nursery Class"
        },
        {
            "fieldname": "assigned_teacher",
            "label": __("Teacher"),
            "fieldtype": "Link",
            "options": "Teacher Profile"
        }
    ]
};
