frappe.query_reports["Attendance Summary"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "nursery_class",
			label: __("Class"),
			fieldtype: "Link",
			options: "Nursery Class",
		},
		{
			fieldname: "child",
			label: __("Child"),
			fieldtype: "Link",
			options: "Child",
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Link",
			options: "Attendance Status",
		},
		{
			fieldname: "group_by_child",
			label: __("Summarise per Child"),
			fieldtype: "Check",
		}
	],
};
