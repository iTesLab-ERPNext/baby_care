frappe.query_reports["Parent Account Statement"] = {
	filters: [
		{
			fieldname: "customer",
			label: __("Parent"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
		}
	],
};
