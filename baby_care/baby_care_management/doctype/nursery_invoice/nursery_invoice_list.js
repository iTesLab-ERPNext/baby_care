frappe.listview_settings["Nursery Invoice"] = {
	add_fields: ["status", "outstanding_amount", "grand_total"],
	get_indicator(doc) {
		const colors = { Draft: "red", Unpaid: "orange", "Partly Paid": "yellow", Paid: "green", Overdue: "red", Cancelled: "gray" };
		return [__(doc.status), colors[doc.status] || "gray", "status,=," + doc.status];
	},
};
