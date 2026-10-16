frappe.query_reports["Subscription Status Report"] = {
    "filters": [
        {
            "fieldname": "status",
            "label": __("Status"),
            "fieldtype": "Select",
            "options": "\nActive\nPending\nSuspended\nExpired\nCancelled",
            "default": "Active"
        }
    ]
};
