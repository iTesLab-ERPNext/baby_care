frappe.ui.form.on("Child", {
	refresh(frm) {
		const colors = { Active: "green", Pending: "orange", Suspended: "red", Withdrawn: "gray", Graduated: "blue" };
		if (frm.doc.enrollment_status) frm.page.set_indicator(__(frm.doc.enrollment_status), colors[frm.doc.enrollment_status] || "gray");
		if (frm.is_new()) return;

		const view = (label, doctype, filters) =>
			frappe.model.can_read(doctype) && frm.add_custom_button(__(label), () => frappe.set_route("List", doctype, filters), __("View"));
		view("Medical Record", "Medical Record", { child: frm.doc.name });
		view("Health Incidents", "Health Incident", { child: frm.doc.name });
		view("Attendance", "Child Attendance", { child: frm.doc.name });
		view("Documents", "Child Document", { child: frm.doc.name });
		view("Subscriptions", "Child Subscription", { child: frm.doc.name });
		view("Meal Plans", "Child Meal Plan", { child: frm.doc.name });
		view("Services", "Child Service Assignment", { child: frm.doc.name });

		const create = (label, doctype, extra) =>
			frappe.model.can_create(doctype) &&
			frm.add_custom_button(__(label), () => frappe.new_doc(doctype, Object.assign({ child: frm.doc.name }, extra || {})), __("Create"));
		const primary = (frm.doc.parents || []).find((p) => p.is_primary) || (frm.doc.parents || [])[0];
		create("Subscription", "Child Subscription", { parent_customer: primary ? primary.parent_customer : "" });
		create("Attendance", "Child Attendance");
		create("Health Incident", "Health Incident");
		create("Document", "Child Document", { document_for: "Child" });
		create("Meal Plan", "Child Meal Plan");
		create("Transportation", "Child Transportation");

		frm.call("get_profile_summary").then((r) => {
			const s = r.message || {};
			(s.alerts || []).forEach((a) => frm.dashboard.add_comment(a, "red", true));
			if ((s.attendance || []).length) {
				const rows = s.attendance
					.map((a) => `<tr><td>${frappe.datetime.str_to_user(a.attendance_date)}</td><td>${__(a.status || "")}</td><td>${a.check_in_time || ""}</td><td>${a.check_out_time || ""}</td></tr>`)
					.join("");
				frm.dashboard.add_section(
					`<table class="table table-sm table-bordered"><thead><tr><th>${__("Date")}</th><th>${__("Status")}</th><th>${__("In")}</th><th>${__("Out")}</th></tr></thead><tbody>${rows}</tbody></table>`,
					__("Recent Attendance")
				);
			}
		});
	},
	setup(frm) {
		frm.set_query("assigned_teacher", () => ({ filters: { employment_status: "Active" } }));
		frm.set_query("nursery_class", () => ({ filters: { status: "Active" } }));
	},
	first_name: (frm) => set_full_name(frm),
	last_name: (frm) => set_full_name(frm),
});

function set_full_name(frm) {
	frm.set_value("full_name", `${frm.doc.first_name || ""} ${frm.doc.last_name || ""}`.trim());
}
