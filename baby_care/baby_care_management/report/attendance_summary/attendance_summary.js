frappe.query_reports["Attendance Summary"] = {
    "filters": [
        {
            "fieldname": "attendance_date",
            "label": __("Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today()
        },
        {
            "fieldname": "nursery_class",
            "label": __("Class"),
            "fieldtype": "Link",
            "options": "Nursery Class"
        }
    ]
};
