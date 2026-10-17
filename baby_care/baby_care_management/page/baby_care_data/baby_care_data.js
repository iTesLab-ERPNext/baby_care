frappe.pages["baby-care-data"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Baby Care Data Management"),
		single_column: true,
	});
	const api = "baby_care.baby_care_management.api.seed.";
	const $body = $(`
		<div class="bc-data">
			<p class="text-muted">${__("Install configuration defaults and a starter catalogue, or load clearly-tagged demo records to try the application. Demo records are tracked and can be removed in one click; real records are never touched.")}</p>
			<div class="bc-actions" style="display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 20px"></div>
			<div class="bc-status"></div>
		</div>`).appendTo(page.body);

	const run = (method, confirm_msg) => {
		const go = () =>
			frappe.call({ method: api + method, freeze: true, freeze_message: __("Working…") }).then((r) => {
				const m = r.message || {};
				frappe.show_alert({ message: __("Done") + (m.created !== undefined ? ` — ${m.created} ${__("created")}` : m.removed !== undefined ? ` — ${m.removed} ${__("removed")}` : ""), indicator: "green" });
				refresh();
			});
		confirm_msg ? frappe.confirm(confirm_msg, go) : go();
	};

	const actions = [
		[__("Install Seed Data"), "btn-primary", () => run("install_seed_data")],
		[__("Install Test Data"), "btn-default", () => run("install_test_data", __("Create demo parents, children, teachers, attendance and subscriptions (tagged [TEST])?"))],
		[__("Refresh Data Status"), "btn-default", () => refresh()],
		[__("Clear Test Data"), "btn-danger", () => run("clear_test_data", __("Delete every tracked demo record, cancelling demo invoices and subscriptions first?"))],
	];
	actions.forEach(([label, cls, fn]) => $(`<button class="btn btn-sm ${cls}">${label}</button>`).on("click", fn).appendTo($body.find(".bc-actions")));

	const refresh = () =>
		frappe.call(api + "get_status").then((r) => {
			const s = r.message;
			const rows = Object.entries(s.counts)
				.map(([dt, n]) => `<tr><td><a href="/app/${frappe.router.slug(dt)}">${__(dt)}</a></td><td class="text-right">${n}</td><td class="text-right text-muted">${s.test_data[dt] || ""}</td></tr>`)
				.join("");
			$body.find(".bc-status").html(`
				<div class="mb-2">${s.test_installed ? `<span class="indicator-pill orange">${__("Test data installed")}</span>` : `<span class="indicator-pill green">${__("No test data")}</span>`}</div>
				<table class="table table-bordered" style="max-width:640px">
					<thead><tr><th>${__("Record type")}</th><th class="text-right">${__("Total")}</th><th class="text-right">${__("Test records")}</th></tr></thead>
					<tbody>${rows}</tbody>
				</table>`);
		});
	refresh();
};
