frappe.query_reports["Parent Account Statement"] = {
	filters: [
		{
			fieldname: "parent_profile",
			label: __("Parent"),
			fieldtype: "Link",
			options: "Parent Profile",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
		}
	],
	onload(report) {
		// Opened from a Parent Profile: the parent arrives through the route after
		// the first (empty) run, and a Link that shows a title does not re-run it.
		setTimeout(() => {
			if (report.get_filter_value("parent_profile") && !(report.data || []).length) report.refresh();
		}, 600);
	},
};
