frappe.query_reports["Revenue Report"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.defaults.get_user_default("year_start_date") || frappe.datetime.year_start(),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "group_by",
			label: __("Group By"),
			fieldtype: "Select",
			options: "Invoice\nMonth\nQuarter\nSubscription Plan\nParent\nChild",
			default: "Month",
		},
		{
			fieldname: "customer",
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
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
		}
	],
};
