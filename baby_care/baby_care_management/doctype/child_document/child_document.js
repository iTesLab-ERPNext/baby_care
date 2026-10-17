frappe.ui.form.on("Child Document", {
	setup(frm) {
		frm.set_query("document_type", () => ({
			filters: { is_active: 1, applies_to: ["in", [frm.doc.document_for || "Child", "Both"]] },
		}));
	},
	document_for(frm) {
		frm.set_value(frm.doc.document_for === "Parent" ? "child" : "parent_customer", "");
		frm.set_value("document_type", "");
	},
	refresh(frm) {
		const colors = { Valid: "green", Expired: "red", Missing: "orange", Revoked: "gray" };
		if (frm.doc.status) frm.page.set_indicator(__(frm.doc.status), colors[frm.doc.status]);
	},
});
