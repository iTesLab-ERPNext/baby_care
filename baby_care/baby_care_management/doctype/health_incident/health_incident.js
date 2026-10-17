frappe.ui.form.on("Health Incident", {
	setup(frm) {
		frm.set_query("child", () => ({ filters: { enrollment_status: "Active" } }));
	},
	refresh(frm) {
		const colors = { Minor: "blue", Moderate: "orange", Serious: "red", Emergency: "red" };
		if (frm.doc.severity) frm.page.set_indicator(__(frm.doc.severity), colors[frm.doc.severity]);
	},
	notified_parent(frm) {
		frm.set_value("parent_notified_at", frm.doc.notified_parent ? frappe.datetime.now_datetime() : "");
	},
});
