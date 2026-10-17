frappe.query_reports["Vaccination Status"] = {
	filters: [
		{
			fieldname: "child",
			label: __("Child"),
			fieldtype: "Link",
			options: "Child",
		},
		{
			fieldname: "only_due",
			label: __("Only Due / Overdue"),
			fieldtype: "Check",
		}
	],
};
