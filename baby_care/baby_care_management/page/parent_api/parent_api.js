// Desk page /app/parent-api — list view of the Parent API endpoints.
// The data comes from the same OpenAPI spec as the public docs page (/parent-api).
frappe.pages["parent-api"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Parent API"), single_column: true });
	const SPEC_URL = "/api/method/baby_care.api.v1.openapi";
	const esc = frappe.utils.escape_html;
	// escape each part separately: frappe's escape_html also escapes the backtick itself
	const code = (s) => String(s == null ? "" : s).split("`").map((part, i) => (i % 2 ? `<code>${esc(part)}</code>` : esc(part))).join("");
	let endpoints = [];

	page.set_primary_action(__("Open Docs & Try it"), () => window.open("/parent-api", "_blank"), "es-line-arrow-up-right");
	page.add_inner_button(__("Download OpenAPI JSON"), () => window.open(SPEC_URL, "_blank"));
	page.add_inner_button(__("Copy Base URL"), () => frappe.utils.copy_to_clipboard(`${window.location.origin}/api/method/baby_care.api.v1.`));

	const tag = page.add_field({ fieldname: "tag", label: __("Group"), fieldtype: "Select", options: [""], change: () => render() });
	const search = page.add_field({ fieldname: "search", label: __("Search"), fieldtype: "Data", change: () => render() });
	search.$input.on("input", frappe.utils.debounce(() => render(), 150));

	const $body = $(`
		<div class="bc-api">
			<p class="text-muted bc-api-intro"></p>
			<div class="bc-api-count text-muted small mb-2"></div>
			<div class="frappe-card bc-api-card">
				<table class="table table-hover bc-api-table mb-0">
					<thead><tr>
						<th style="width:80px">${__("Method")}</th>
						<th>${__("Endpoint")}</th>
						<th class="hidden-xs">${__("Group")}</th>
						<th>${__("Description")}</th>
						<th class="hidden-xs" style="width:120px">${__("Access")}</th>
					</tr></thead>
					<tbody></tbody>
				</table>
			</div>
		</div>`).appendTo(page.body);

	function badge(m) {
		return `<span class="indicator-pill no-indicator-dot ${m === "GET" ? "green" : "orange"}" style="font-family:var(--font-stack-monospace, monospace)">${m}</span>`;
	}

	function detail(ep) {
		const params = ep.params.length
			? `<table class="table table-sm table-bordered mt-2"><thead><tr><th>${__("Parameter")}</th><th>${__("Type")}</th><th>${__("Required")}</th><th>${__("Description")}</th><th>${__("Example")}</th></tr></thead><tbody>${ep.params
					.map((p) => `<tr><td><code>${esc(p.name)}</code></td><td>${esc(p.type)}</td><td>${p.required ? __("Yes") : ""}</td><td>${code(p.description)}</td><td><code>${esc(String(p.example ?? ""))}</code></td></tr>`)
					.join("")}</tbody></table>`
			: `<p class="text-muted mt-2">${__("No parameters.")}</p>`;
		const url = `${window.location.origin}${ep.path}`;
		const example = Object.fromEntries(ep.params.filter((p) => p.required).map((p) => [p.name, p.example]));
		const curl =
			ep.method === "GET"
				? `curl -b cookies.txt "${url}${Object.keys(example).length ? "?" + new URLSearchParams(example) : ""}"`
				: `curl -c cookies.txt -b cookies.txt -X POST "${url}" -H "Content-Type: application/json"${Object.keys(example).length ? ` -d '${JSON.stringify(example)}'` : ""}`;
		return `
			<tr class="bc-api-detail"><td colspan="5" style="background:var(--subtle-fg)">
				<p class="mb-2">${code(ep.description)}</p>
				<div class="mb-2"><b>${__("URL")}</b> <code>${esc(url)}</code>
					<button class="btn btn-xs btn-default ml-2 bc-copy" data-copy="${esc(url)}">${__("Copy")}</button></div>
				${params}
				<div class="row">
					<div class="col-md-6"><b>${__("Example request")}</b>
						<button class="btn btn-xs btn-default ml-2 bc-copy" data-copy="${esc(curl)}">${__("Copy")}</button>
						<pre class="mt-1" style="white-space:pre-wrap;max-height:240px;overflow:auto">${esc(curl)}</pre></div>
					<div class="col-md-6"><b>${__("Example response")}</b>
						<pre class="mt-1" style="max-height:240px;overflow:auto">${esc(JSON.stringify({ message: ep.example }, null, 2))}</pre></div>
				</div>
			</td></tr>`;
	}

	function render() {
		const t = tag.get_value();
		const q = (search.get_value() || "").toLowerCase().trim();
		const rows = endpoints.filter(
			(ep) => (!t || ep.tag === t) && (!q || [ep.name, ep.summary, ep.description, ep.tag].join(" ").toLowerCase().includes(q))
		);
		$body.find(".bc-api-count").text(__("{0} of {1} endpoints", [rows.length, endpoints.length]));
		$body.find("tbody").html(
			rows.length
				? rows
						.map(
							(ep) => `
					<tr class="bc-api-row" data-name="${esc(ep.name)}" style="cursor:pointer">
						<td>${badge(ep.method)}</td>
						<td><code>${esc(ep.name)}</code></td>
						<td class="hidden-xs text-muted">${esc(__(ep.tag))}</td>
						<td>${esc(ep.summary)}</td>
						<td class="hidden-xs">${ep.public ? `<span class="text-muted">${__("Public")}</span>` : `${frappe.utils.icon("lock", "xs")} ${__("Parent login")}`}</td>
					</tr>`
						)
						.join("")
				: `<tr><td colspan="5" class="text-muted text-center p-4">${__("No endpoints match.")}</td></tr>`
		);
	}

	$body.on("click", ".bc-api-row", function () {
		const $row = $(this);
		const open = $row.next().hasClass("bc-api-detail");
		$body.find(".bc-api-detail").remove();
		$body.find(".bc-api-row").removeClass("active");
		if (open) return;
		const ep = endpoints.find((e) => e.name === $row.attr("data-name"));
		$row.addClass("active").after(detail(ep));
	});
	$body.on("click", ".bc-copy", function (e) {
		e.stopPropagation();
		frappe.utils.copy_to_clipboard($(this).attr("data-copy"));
	});

	fetch(SPEC_URL, { credentials: "same-origin" })
		.then((r) => r.json())
		.then((spec) => {
			$body.find(".bc-api-intro").html(
				__("Read-only API for parents (mobile app / parent portal), version {0}. Every call returns only the logged-in parent's own data. Give a parent access from their Customer record: <b>Baby Care → Create Parent Login</b>.", [esc(spec.info.version)])
			);
			Object.entries(spec.paths).forEach(([path, ops]) =>
				Object.entries(ops).forEach(([m, op]) => {
					const body = ((op.requestBody || {}).content || {})["application/json"];
					const params = op.parameters
						? op.parameters.map((p) => ({ name: p.name, type: p.schema.type, required: p.required, description: p.description, example: p.example }))
						: body
						? Object.entries(body.schema.properties).map(([name, p]) => ({ name, type: p.type, required: (body.schema.required || []).includes(name), description: p.description, example: p.example }))
						: [];
					endpoints.push({
						name: op.operationId, method: m.toUpperCase(), path, tag: op.tags[0], summary: op.summary,
						description: op.description, public: Array.isArray(op.security) && !op.security.length, params,
						example: op.responses["200"].content["application/json"].example.message,
					});
				})
			);
			tag.df.options = [""].concat([...new Set(endpoints.map((e) => e.tag))]);
			tag.refresh();
			render();
		})
		.catch((err) => $body.find(".bc-api-intro").text(__("Could not load the API description: {0}", [err])));
};
