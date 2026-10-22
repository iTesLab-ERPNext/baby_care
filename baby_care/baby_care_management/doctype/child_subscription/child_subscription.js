frappe.ui.form.on("Child Subscription", {
	setup(frm) {
		frm.set_query("subscription_plan", () => ({ filters: { is_active: 1 } }));
		frm.set_query("parent_customer", () => {
			const parents = frm.__child_parents || [];
			return parents.length ? { filters: { name: ["in", parents] } } : {};
		});
	},
	onload(frm) {
		if (frm.fields_dict.additional_services && frm.fields_dict.additional_services.grid) {
			frm.set_query("service", "additional_services", () => ({ filters: { is_active: 1, is_optional: 1 } }));
		}
	},
	child(frm) {
		if (!frm.doc.child) return;
		frappe.db.get_doc("Child", frm.doc.child).then((c) => {
			frm.__child_parents = (c.parents || []).map((p) => p.parent_customer);
			const primary = (c.parents || []).find((p) => p.is_primary) || (c.parents || [])[0];
			if (primary && !frm.doc.parent_customer) frm.set_value("parent_customer", primary.parent_customer);
		});
	},
	refresh(frm) {
		const colors = { Draft: "red", Active: "green", Pending: "orange", Suspended: "red", Expired: "gray", Cancelled: "red" };
		if (frm.doc.status) frm.page.set_indicator(__(frm.doc.status), colors[frm.doc.status] || "gray");
		if (frm.doc.docstatus !== 1 || !frm.has_perm("write")) return;
		const act = (label, method, args, confirm) =>
			frm.add_custom_button(__(label), () => {
				const go = (extra) => frm.call(method, Object.assign({}, args, extra)).then(() => frm.reload_doc());
				if (confirm === "reason") frappe.prompt({ fieldname: "reason", fieldtype: "Small Text", label: __("Reason"), reqd: 1 }, (v) => go(v), __(label));
				else if (confirm) frappe.confirm(confirm, () => go());
				else go();
			}, __("Actions"));
		if (frm.doc.status === "Active") {
			frm.add_custom_button(__("Generate Invoice"), () =>
				frm.call("generate_invoice").then((r) => {
					frm.reload_doc();
					if (r.message) frappe.set_route("Form", "Sales Invoice", r.message);
				}), __("Actions"));
			act("Suspend", "suspend", {}, "reason");
		}
		if (frm.doc.status === "Suspended") act("Resume", "resume", {});
		if (["Active", "Expired", "Suspended"].includes(frm.doc.status)) act("Renew", "renew", {}, __("Extend this subscription by one plan period?"));
		if (frappe.model.can_read("Sales Invoice"))
			frm.add_custom_button(__("Invoices"), () => frappe.set_route("List", "Sales Invoice", { baby_care_subscription: frm.doc.name }), __("View"));
	},
});

frappe.ui.form.on("Child Subscription Service", {
	qty: (frm, cdt, cdn) => update_row(frm, cdt, cdn),
	rate: (frm, cdt, cdn) => update_row(frm, cdt, cdn),
});

function update_row(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	frappe.model.set_value(cdt, cdn, "amount", flt(row.rate) * flt(row.qty || 1));
}
