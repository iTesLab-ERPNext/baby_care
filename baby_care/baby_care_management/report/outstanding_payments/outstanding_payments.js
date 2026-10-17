frappe.query_reports["Outstanding Payments"] = {
	filters: [
		{
			fieldname: "customer",
			label: __("Parent"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "overdue_only",
			label: __("Overdue Only"),
			fieldtype: "Check",
		}
	],
};
