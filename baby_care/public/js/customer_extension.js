// Baby Care — parent profile on the ERPNext Customer form
frappe.ui.form.on("Customer", {
	refresh(frm) {
		if (frm.is_new()) return;
		const group = __("Baby Care");
		if (frappe.model.can_read("Child"))
			frm.add_custom_button(__("Children"), () => frappe.set_route("List", "Child", { "parents.parent_customer": frm.doc.name }), group);
		if (frappe.model.can_read("Child Subscription"))
			frm.add_custom_button(__("Subscriptions"), () => frappe.set_route("List", "Child Subscription", { parent_customer: frm.doc.name }), group);
		if (frappe.model.can_read("Child Document"))
			frm.add_custom_button(__("Parent Documents"), () => frappe.set_route("List", "Child Document", { parent_customer: frm.doc.name }), group);
		if (frappe.model.can_create("Child"))
			frm.add_custom_button(__("Register Child"), () => frappe.new_doc("Child", { parents: [{ parent_customer: frm.doc.name, is_primary: 1 }] }), group);
		frm.add_custom_button(__("Account Statement"), () => frappe.set_route("query-report", "Parent Account Statement", { customer: frm.doc.name }), group);

		frappe.call("baby_care.baby_care_management.utils.billing.get_parent_statement", { customer: frm.doc.name }).then((r) => {
			const s = r.message;
			if (!s || (!s.children.length && !s.subscriptions.length)) return;
			const esc = frappe.utils.escape_html;
			const kids = s.children
				.map((c) => `<tr><td><a href="/app/child/${encodeURIComponent(c.name)}">${esc(c.full_name)}</a></td><td>${__(c.enrollment_status || "")}</td><td>${esc(c.nursery_class || "")}</td></tr>`)
				.join("");
			const subs = s.subscriptions
				.map((x) => `<tr><td><a href="/app/child-subscription/${encodeURIComponent(x.name)}">${esc(x.name)}</a></td><td>${esc(x.subscription_plan)}</td><td>${__(x.status)}</td><td>${format_currency(x.final_amount)}</td></tr>`)
				.join("");
			let html = "";
			if (kids) html += `<h6>${__("Children")}</h6><table class="table table-sm table-bordered"><tbody>${kids}</tbody></table>`;
			if (subs) html += `<h6>${__("Subscriptions")}</h6><table class="table table-sm table-bordered"><tbody>${subs}</tbody></table>`;
			if (s.invoices.length)
				html += `<p><b>${__("Outstanding")}:</b> ${format_currency(s.outstanding)}${s.next_due ? ` · <b>${__("Next due")}:</b> ${frappe.datetime.str_to_user(s.next_due)}` : ""}</p>`;
			frm.dashboard.add_section(html, __("Baby Care"));
		});
	},
});
