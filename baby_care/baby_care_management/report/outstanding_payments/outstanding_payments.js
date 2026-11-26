frappe.query_reports["Outstanding Payments"] = {
	filters: [
		{
			fieldname: "parent_profile",
			label: __("Parent"),
			fieldtype: "Link",
			options: "Parent Profile",
		},
		{
			fieldname: "overdue_only",
			label: __("Overdue Only"),
			fieldtype: "Check",
		}
	],
};
