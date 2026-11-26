frappe.ui.form.on("Nursery Invoice", {
	setup(frm) {
		frm.set_query("child", () => (frm.doc.parent_profile ? { query: "baby_care.baby_care_management.doctype.nursery_invoice.nursery_invoice.children_of_parent", filters: { parent_profile: frm.doc.parent_profile } } : {}));
		frm.set_query("service", "items", () => ({ filters: { is_active: 1 } }));
	},
	onload(frm) {
		if (frm.is_new() && !frm.doc.currency)
			frappe.db.get_single_value("Nursery Settings", "default_currency").then((c) => c && frm.set_value("currency", c));
		if (frm.is_new() && !flt(frm.doc.tax_rate) && !frm.doc.child_subscription)
			frappe.db.get_single_value("Nursery Settings", "default_tax_rate").then((t) => t && frm.set_value("tax_rate", t));
	},
	refresh(frm) {
		const colors = { Draft: "red", Unpaid: "orange", "Partly Paid": "yellow", Paid: "green", Overdue: "red", Cancelled: "gray" };
		if (frm.doc.status) frm.page.set_indicator(__(frm.doc.status), colors[frm.doc.status] || "gray");
		if (frm.doc.docstatus === 1 && flt(frm.doc.outstanding_amount) > 0 && frappe.model.can_create("Nursery Payment")) {
			frm.add_custom_button(__("Record Payment"), () =>
				frappe.model.with_doctype("Nursery Payment", () => {
					const pay = frappe.model.get_new_doc("Nursery Payment");
					Object.assign(pay, { parent_profile: frm.doc.parent_profile, parent_name: frm.doc.parent_name, currency: frm.doc.currency, amount: frm.doc.outstanding_amount });
					const row = frappe.model.add_child(pay, "Nursery Payment Allocation", "allocations");
					Object.assign(row, { invoice: frm.doc.name, child: frm.doc.child, invoice_total: frm.doc.grand_total, outstanding: frm.doc.outstanding_amount, allocated_amount: frm.doc.outstanding_amount });
					pay.allocated_amount = frm.doc.outstanding_amount;
					pay.unallocated_amount = 0;
					frappe.set_route("Form", "Nursery Payment", pay.name);
				}), null, "primary");
		}
		if (frm.doc.docstatus === 1 && frappe.model.can_read("Nursery Payment"))
			frm.add_custom_button(__("Payments"), () => frappe.set_route("List", "Nursery Payment", { parent_profile: frm.doc.parent_profile }), __("View"));
	},
	discount_percent: (frm) => calc(frm),
	tax_rate: (frm) => calc(frm),
});

frappe.ui.form.on("Nursery Invoice Item", {
	qty: (frm, cdt, cdn) => row(frm, cdt, cdn),
	rate: (frm, cdt, cdn) => row(frm, cdt, cdn),
	items_remove: (frm) => calc(frm),
	service(frm, cdt, cdn) {
		const r = locals[cdt][cdn];
		if (!r.service) return;
		frappe.db.get_value("Nursery Service", r.service, ["service_name", "price"]).then(({ message: s }) => {
			if (!r.description) frappe.model.set_value(cdt, cdn, "description", s.service_name);
			frappe.model.set_value(cdt, cdn, "rate", s.price);
		});
	},
});

function row(frm, cdt, cdn) {
	const r = locals[cdt][cdn];
	frappe.model.set_value(cdt, cdn, "amount", flt(r.rate) * flt(r.qty || 1));
	calc(frm);
}

function calc(frm) {
	const total = (frm.doc.items || []).reduce((s, r) => s + flt(r.amount), 0);
	const disc = flt((total * flt(frm.doc.discount_percent)) / 100, 2);
	const tax = flt(((total - disc) * flt(frm.doc.tax_rate)) / 100, 2);
	frm.set_value({ total, discount_amount: disc, tax_amount: tax, grand_total: flt(total - disc + tax, 2), outstanding_amount: flt(total - disc + tax, 2) });
}
