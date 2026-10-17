frappe.ui.form.on("Child Attendance", {
	onload(frm) {
		// Frappe pre-fills empty Time fields with "now": a new record only
		// keeps the check-in, check-out is entered when the child leaves.
		if (frm.is_new()) frm.set_value("check_out_time", "");
	},
	setup(frm) {
		frm.set_query("child", () => ({ filters: { enrollment_status: "Active" } }));
	},
	refresh(frm) {
		if (frm.is_new() || !frm.doc.child) return;
		if (!frm.doc.check_out_time && frm.has_perm("write")) {
			frm.add_custom_button(__("Check Out Now"), () => pick_up(frm));
		}
	},
	status(frm) {
		frappe.db.get_value("Attendance Status", frm.doc.status, "status_type").then((r) => {
			const t = r.message && r.message.status_type;
			if (["Absent", "Leave", "Holiday"].includes(t)) {
				frm.set_value({ check_in_time: "", check_out_time: "", pickup_person: "" });
			}
		});
	},
});

function pick_up(frm) {
	frappe.call("baby_care.baby_care_management.doctype.child_attendance.child_attendance.get_authorized_pickups", { child: frm.doc.child }).then((r) => {
		const options = r.message || [];
		frappe.prompt(
			[{ fieldname: "pickup_person", fieldtype: options.length ? "Select" : "Data", options: options.join("\n"), label: __("Picked up by"), reqd: 1 }],
			(v) => {
				frm.set_value({ pickup_person: v.pickup_person, check_out_time: frappe.datetime.now_time() });
				frm.save();
			},
			__("Authorized pickup")
		);
	});
}

frappe.listview_settings["Child Attendance"] = {
	add_fields: ["status"],
	onload(list) {
		if (!frappe.model.can_create("Child Attendance")) return;
		list.page.add_inner_button(__("Mark Class Attendance"), () => {
			frappe.prompt(
				[
					{ fieldname: "nursery_class", fieldtype: "Link", options: "Nursery Class", label: __("Class"), reqd: 1 },
					{ fieldname: "attendance_date", fieldtype: "Date", label: __("Date"), default: frappe.datetime.get_today(), reqd: 1 },
					{ fieldname: "status", fieldtype: "Link", options: "Attendance Status", label: __("Status"), default: "Present", reqd: 1 },
				],
				(v) =>
					frappe.call("baby_care.baby_care_management.doctype.child_attendance.child_attendance.mark_class_attendance", v).then((r) => {
						frappe.show_alert({ message: __("{0} attendance records created", [r.message || 0]), indicator: "green" });
						list.refresh();
					}),
				__("Mark Class Attendance")
			);
		});
	},
};
