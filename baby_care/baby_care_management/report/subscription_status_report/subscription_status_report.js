frappe.query_reports["Subscription Status Report"] = {
	filters: [
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nDraft\nActive\nPending\nSuspended\nExpired\nCancelled",
		},
		{
			fieldname: "subscription_plan",
			label: __("Plan"),
			fieldtype: "Link",
			options: "Subscription Plan",
		},
		{
			fieldname: "parent_customer",
			label: __("Parent"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "child",
			label: __("Child"),
			fieldtype: "Link",
			options: "Child",
		},
		{
			fieldname: "expiring_within_days",
			label: __("Expiring Within (days)"),
			fieldtype: "Int",
		}
	],
};
