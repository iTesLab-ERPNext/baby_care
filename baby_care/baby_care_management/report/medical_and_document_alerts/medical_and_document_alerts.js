frappe.query_reports["Medical and Document Alerts"] = {
	filters: [
		{
			fieldname: "within_days",
			label: __("Look Ahead (days)"),
			fieldtype: "Int",
			default: 30,
		},
		{
			fieldname: "severity",
			label: __("Severity"),
			fieldtype: "Select",
			options: "\nHigh\nMedium",
		}
	],
};
