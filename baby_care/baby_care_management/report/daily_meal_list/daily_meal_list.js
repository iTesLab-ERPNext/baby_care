frappe.query_reports["Daily Meal List"] = {
	filters: [
		{
			fieldname: "date",
			label: __("Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "nursery_class",
			label: __("Class"),
			fieldtype: "Link",
			options: "Nursery Class",
		}
	],
};
