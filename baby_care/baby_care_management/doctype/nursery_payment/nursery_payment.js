frappe.ui.form.on("Nursery Payment", {
	onload(frm) {
		if (frm.is_new() && !frm.doc.currency)
			frappe.db.get_single_value("Nursery Settings", "default_currency").then((c) => c && frm.set_value("currency", c));
	},
	setup(frm) {
		frm.set_query("invoice", "allocations", () => ({
			filters: { parent_profile: frm.doc.parent_profile, docstatus: 1, outstanding_amount: [">", 0] },
		}));
	},
	refresh(frm) {
		if (frm.doc.docstatus === 0 && frm.doc.parent_profile)
			frm.add_custom_button(__("Get Unpaid Invoices"), () => fill(frm));
		if (frm.doc.docstatus === 1 && flt(frm.doc.unallocated_amount) > 0)
			frm.dashboard.add_comment(__("{0} not allocated: kept as a credit for this parent.", [format_currency(frm.doc.unallocated_amount, frm.doc.currency)]), "blue", true);
	},
	parent_profile(frm) {
		// Frappe also fires this while a prefilled form loads, so only drop rows
		// whose invoice belongs to another parent.
		const rows = (frm.doc.allocations || []).filter((r) => r.invoice);
		if (!rows.length) return;
		frappe.db.get_list("Nursery Invoice", { filters: { name: ["in", rows.map((r) => r.invoice)] }, fields: ["name", "parent_profile"] }).then((list) => {
			const owner = Object.fromEntries(list.map((i) => [i.name, i.parent_profile]));
			const keep = (frm.doc.allocations || []).filter((r) => !r.invoice || owner[r.invoice] === frm.doc.parent_profile);
			if (keep.length === (frm.doc.allocations || []).length) return;
			frm.doc.allocations = keep;
			keep.forEach((r, i) => (r.idx = i + 1));
			frm.refresh_field("allocations");
			totals(frm);
		});
	},
	amount: (frm) => totals(frm),
});

frappe.ui.form.on("Nursery Payment Allocation", {
	allocated_amount: (frm) => totals(frm),
	allocations_remove: (frm) => totals(frm),
	invoice(frm, cdt, cdn) {
		const r = locals[cdt][cdn];
		if (!r.invoice) return;
		frappe.db.get_value("Nursery Invoice", r.invoice, ["outstanding_amount", "grand_total", "child"]).then(({ message: i }) => {
			frappe.model.set_value(cdt, cdn, { outstanding: i.outstanding_amount, invoice_total: i.grand_total, child: i.child, allocated_amount: i.outstanding_amount });
		});
	},
});

function fill(frm) {
	frappe.call({
		method: "baby_care.baby_care_management.doctype.nursery_payment.nursery_payment.get_open_invoices",
		args: { parent_profile: frm.doc.parent_profile, payment: frm.is_new() ? null : frm.doc.name },
	}).then(({ message: rows }) => {
		frm.clear_table("allocations");
		let left = flt(frm.doc.amount) || (rows || []).reduce((s, r) => s + flt(r.outstanding_amount), 0);
		if (!flt(frm.doc.amount)) frm.set_value("amount", left);
		(rows || []).forEach((r) => {
			if (left <= 0) return;
			const take = Math.min(left, flt(r.outstanding_amount));
			frm.add_child("allocations", { invoice: r.name, child: r.child, invoice_total: r.grand_total, outstanding: r.outstanding_amount, allocated_amount: take });
			left -= take;
		});
		frm.refresh_field("allocations");
		totals(frm);
	});
}

function totals(frm) {
	const alloc = (frm.doc.allocations || []).reduce((s, r) => s + flt(r.allocated_amount), 0);
	frm.set_value({ allocated_amount: alloc, unallocated_amount: flt(frm.doc.amount) - alloc });
}
