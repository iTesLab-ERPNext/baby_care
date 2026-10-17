frappe.query_reports["Parent Account Statement"] = {
	filters: [
		{
			fieldname: "customer",
			label: __("Parent"),
			fieldtype: "Link",
			options: "Customer",
			reqd: 1,
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
		}
	],
};
