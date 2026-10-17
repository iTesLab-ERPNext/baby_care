frappe.ui.form.on("Teacher Profile", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Assigned Children"), () => frappe.set_route("List", "Child", { assigned_teacher: frm.doc.name }), __("View"));
		frm.call("get_assigned_children").then((r) => {
			const kids = r.message || [];
			if (!kids.length) return;
			const rows = kids
				.map((k) => `<tr><td><a href="/app/child/${encodeURIComponent(k.name)}">${frappe.utils.escape_html(k.full_name)}</a>${k.has_allergies ? ` <span class="indicator-pill red">${__("Allergies")}</span>` : ""}</td><td>${k.nursery_class || ""}</td><td>${k.age_display || ""}</td></tr>`)
				.join("");
			frm.dashboard.add_section(
				`<table class="table table-sm table-bordered"><thead><tr><th>${__("Child")}</th><th>${__("Class")}</th><th>${__("Age")}</th></tr></thead><tbody>${rows}</tbody></table>`,
				__("Assigned Children ({0})", [kids.length])
			);
		});
	},
});
