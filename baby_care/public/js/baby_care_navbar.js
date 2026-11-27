// Baby Care — navigation menus built from frappe.boot.baby_care_menu
// (same sections as the workspace, filtered by the user's permissions on the server):
//   1. "Baby Care ▾" dropdown in the navbar
//   2. collapsible tree under "Baby Care Management" in the workspace sidebar
(function () {
	const WORKSPACE_TITLE = "Baby Care Management";
	const ICON = (name, size = "sm") => `<svg class="icon icon-${size}"><use href="#icon-${name}"></use></svg>`;

	const storage = (key) => ({
		get(fallback) {
			try {
				const v = JSON.parse(localStorage.getItem(key) || "null");
				return v === null ? fallback : v;
			} catch (e) {
				return fallback;
			}
		},
		set(value) {
			try {
				localStorage.setItem(key, JSON.stringify(value));
			} catch (e) {
				/* storage unavailable: state just isn't remembered */
			}
		},
	});

	const esc = (s) => frappe.utils.escape_html(String(s == null ? "" : s));
	const path = (route) => decodeURIComponent(route || "").replace(/\/$/, "");
	const current = () => path(window.location.pathname);
	const href = (route) => route.split("/").map((p) => encodeURIComponent(decodeURIComponent(p))).join("/");
	const menu = () => frappe.boot && frappe.boot.baby_care_menu;
	const kindLabel = (k) => (k === "Report" ? __("Report") : k === "Dashboard" ? __("Dashboard") : "");

	function highlight(text, q) {
		const t = esc(text);
		if (!q) return t;
		const i = text.toLowerCase().indexOf(q);
		return i < 0 ? t : esc(text.slice(0, i)) + "<mark>" + esc(text.slice(i, i + q.length)) + "</mark>" + esc(text.slice(i + q.length));
	}

	/** Shared renderer for both menus. `prefix` keeps element ids unique. */
	function renderSections(m, { prefix, query, openSections }) {
		const q = (query || "").trim().toLowerCase();
		const here = current();
		let html = "";
		let shown = 0;
		m.sections.forEach((s, idx) => {
			const title = __(s.label);
			const titleHit = q && title.toLowerCase().includes(q);
			const items = s.items.filter((it) => !q || titleHit || __(it.label).toLowerCase().includes(q));
			if (!items.length) return;
			shown++;
			const containsHere = s.items.some((it) => path(it.route) === here);
			const expanded = q ? true : openSections ? openSections.includes(s.label) || containsHere : containsHere;
			const id = `${prefix}-sec-${idx}`;
			html += `
				<div class="bc-nav-section${expanded ? " expanded" : ""}" data-section="${esc(s.label)}">
					<button type="button" class="bc-nav-sec-btn" aria-expanded="${expanded}" aria-controls="${id}">
						<span class="bc-nav-chevron">${ICON("right", "xs")}</span>
						<span class="bc-nav-sec-title">${highlight(title, q)}</span>
						<span class="bc-nav-count">${items.length}</span>
					</button>
					<div class="bc-nav-items" id="${id}" role="group">
						${items
							.map((it) => {
								const label = __(it.label);
								const kind = kindLabel(it.kind);
								return `<a class="bc-nav-link${path(it.route) === here ? " active" : ""}" href="${href(it.route)}" data-route="${esc(it.route)}" title="${esc(label)}">${highlight(label, q)}${kind ? `<span class="bc-nav-kind">${esc(kind)}</span>` : ""}</a>`;
							})
							.join("")}
					</div>
				</div>`;
		});
		if (!shown) html += `<div class="bc-nav-empty">${esc(__("No matching pages"))}</div>`;
		return html;
	}

	const openSectionsOf = ($root) => $root.find(".bc-nav-section.expanded").map((_, el) => $(el).attr("data-section")).get();

	function followLink(e, $a, after) {
		// let the browser handle new-tab / new-window clicks
		if (e.ctrlKey || e.metaKey || e.shiftKey || e.button === 1) return;
		e.preventDefault();
		after && after();
		frappe.set_route($a.attr("data-route"));
	}

	function markActive($root) {
		const here = current();
		$root.find(".bc-nav-link").each(function () {
			$(this).toggleClass("active", path($(this).attr("data-route")) === here);
		});
	}

	// ── route change wiring ──────────────────────────────────────────────
	const routeHandlers = [];
	let routerHooked = false;
	function onRouteChange(fn) {
		routeHandlers.push(fn);
		hookRouter();
	}
	function hookRouter() {
		if (routerHooked || !frappe.router || !frappe.router.on) return;
		routerHooked = true;
		frappe.router.on("change", () => setTimeout(() => routeHandlers.forEach((fn) => fn()), 0));
	}

	// ── 1. navbar dropdown ────────────────────────────────────────────────
	function buildNavbar() {
		const m = menu();
		const $brand = $(".navbar .navbar-brand").first();
		if (!m || !m.sections || !m.sections.length || !$brand.length || $(".bc-nav").length) return;
		const store = storage("baby_care_navbar_open_sections");

		const $nav = $(`
			<div class="bc-nav">
				<button type="button" class="bc-nav-toggle" aria-haspopup="true" aria-expanded="false" aria-controls="bc-nav-panel" title="${esc(__("Baby Care menu"))}">
					<img src="/assets/baby_care/images/baby_care_logo.svg" alt="">
					<span class="bc-nav-label">${esc(__("Baby Care"))}</span>
					<span class="bc-nav-caret">${ICON("down", "xs")}</span>
				</button>
				<div class="bc-nav-panel" id="bc-nav-panel" role="menu">
					<div class="bc-nav-head">
						<input type="search" class="bc-nav-filter" placeholder="${esc(__("Filter menu…"))}" aria-label="${esc(__("Filter menu"))}">
						<button type="button" class="bc-nav-tool" data-action="toggle-all">${esc(__("Expand all"))}</button>
					</div>
					<div class="bc-nav-body"></div>
				</div>
			</div>`);
		$brand.after($nav);

		const $body = $nav.find(".bc-nav-body");
		const $filter = $nav.find(".bc-nav-filter");
		const $toggleAll = $nav.find('[data-action="toggle-all"]');

		function render(query) {
			const home = query
				? ""
				: `<a class="bc-nav-home" href="${href(m.workspace.route)}" data-route="${esc(m.workspace.route)}">${ICON("dashboard")}<span>${esc(__(m.workspace.label))}</span></a>`;
			$body.html(home + renderSections(m, { prefix: "bc-nav", query, openSections: store.get(null) }));
			refreshToggleAll();
		}
		function refreshToggleAll() {
			const all = $body.find(".bc-nav-section");
			const allOpen = all.length && all.length === all.filter(".expanded").length;
			$toggleAll.text(allOpen ? __("Collapse all") : __("Expand all")).data("expand", !allOpen);
		}
		function setOpen(open) {
			$nav.toggleClass("open", open);
			$nav.find(".bc-nav-toggle").attr("aria-expanded", open);
			if (open) {
				$filter.val("");
				render();
				setTimeout(() => $filter.trigger("focus"), 0);
			}
		}

		$nav.on("click", ".bc-nav-toggle", (e) => {
			e.stopPropagation();
			setOpen(!$nav.hasClass("open"));
		});
		$nav.on("click", ".bc-nav-sec-btn", function () {
			const $sec = $(this).closest(".bc-nav-section").toggleClass("expanded");
			$(this).attr("aria-expanded", $sec.hasClass("expanded"));
			if (!$filter.val()) store.set(openSectionsOf($body));
			refreshToggleAll();
		});
		$toggleAll.on("click", () => {
			const expand = !!$toggleAll.data("expand");
			$body.find(".bc-nav-section").toggleClass("expanded", expand).find(".bc-nav-sec-btn").attr("aria-expanded", expand);
			if (!$filter.val()) store.set(openSectionsOf($body));
			refreshToggleAll();
		});
		$filter.on("input", frappe.utils.debounce(() => render($filter.val()), 120));
		$filter.on("keydown", (e) => {
			if (e.key === "Enter") {
				const first = $body.find(".bc-nav-link").first();
				if (first.length) first[0].click();
			}
		});
		$nav.on("click", ".bc-nav-link, .bc-nav-home", function (e) {
			followLink(e, $(this), () => setOpen(false));
		});
		$(document).on("click.bc_nav", (e) => {
			if ($nav.hasClass("open") && !$(e.target).closest(".bc-nav").length) setOpen(false);
		});
		$(document).on("keydown.bc_nav", (e) => {
			if (e.key === "Escape" && $nav.hasClass("open")) {
				setOpen(false);
				$nav.find(".bc-nav-toggle").trigger("focus");
			}
		});
		onRouteChange(() => $nav.hasClass("open") && setOpen(false));
	}

	// ── 2. workspace sidebar tree ─────────────────────────────────────────
	const sideSections = storage("baby_care_sidebar_open_sections");
	const sideCollapsed = storage("baby_care_sidebar_collapsed");

	function isInsideApp(m) {
		const here = current();
		return here === path(m.workspace.route) || m.sections.some((s) => s.items.some((it) => path(it.route) === here));
	}

	function attachSidebar() {
		const m = menu();
		if (!m || !m.sections || !m.sections.length) return;
		$(".desk-sidebar .sidebar-item-container").each(function () {
			const $item = $(this);
			if ($item.attr("item-name") !== WORKSPACE_TITLE || $item.children(".bc-side").length) return;

			let collapsed = sideCollapsed.get(null);
			if (collapsed === null) collapsed = !isInsideApp(m);

			const $tree = $(`<div class="bc-side${collapsed ? " collapsed" : ""}" role="navigation" aria-label="${esc(__("Baby Care menu"))}"></div>`);
			$tree.html(renderSections(m, { prefix: "bc-side", openSections: sideSections.get([]) }));
			$item.children(".desk-sidebar-item").after($tree);

			const $control = $item.find("> .desk-sidebar-item .sidebar-item-control");
			const $toggle = $(
				`<button type="button" class="btn-reset bc-side-toggle" aria-expanded="${!collapsed}" title="${esc(__("Show or hide Baby Care pages"))}">${ICON("down", "sm")}</button>`
			).appendTo($control);

			$toggle.on("click", (e) => {
				e.preventDefault();
				e.stopPropagation();
				const nowCollapsed = !$tree.hasClass("collapsed");
				$tree.toggleClass("collapsed", nowCollapsed);
				$toggle.attr("aria-expanded", !nowCollapsed);
				sideCollapsed.set(nowCollapsed);
			});
			$tree.on("click", ".bc-nav-sec-btn", function () {
				const $sec = $(this).closest(".bc-nav-section").toggleClass("expanded");
				$(this).attr("aria-expanded", $sec.hasClass("expanded"));
				sideSections.set(openSectionsOf($tree));
			});
			$tree.on("click", ".bc-nav-link", function (e) {
				followLink(e, $(this));
			});
		});
	}

	function refreshSidebar() {
		const m = menu();
		$(".bc-side").each(function () {
			const $tree = $(this);
			markActive($tree);
			// entering a Baby Care page opens the tree, unless the user collapsed it on purpose
			if (m && $tree.hasClass("collapsed") && sideCollapsed.get(null) === null && isInsideApp(m)) {
				$tree.removeClass("collapsed");
				$tree.closest(".sidebar-item-container").find(".bc-side-toggle").attr("aria-expanded", true);
			}
			// open the section of the page we navigated to
			const $sec = $tree.find(".bc-nav-link.active").closest(".bc-nav-section");
			if ($sec.length && !$sec.hasClass("expanded")) {
				$sec.addClass("expanded").find(".bc-nav-sec-btn").attr("aria-expanded", true);
			}
		});
	}

	let scheduled = false;
	function scheduleAttach() {
		if (scheduled) return;
		scheduled = true;
		requestAnimationFrame(() => {
			scheduled = false;
			attachSidebar();
			// Frappe may re-render the sidebar after the route event: re-sync highlights
			const here = current();
			if (here !== scheduleAttach.lastPath) {
				scheduleAttach.lastPath = here;
				refreshSidebar();
			}
		});
	}

	function init() {
		if (!menu()) return;
		buildNavbar(); // idempotent
		attachSidebar(); // idempotent
		if (init.wired) return;
		init.wired = true;
		onRouteChange(refreshSidebar);
		// Frappe rebuilds the workspace sidebar (page switches, edit mode…): re-attach.
		new MutationObserver(scheduleAttach).observe(document.body, { childList: true, subtree: true });
	}

	$(document).on("app_ready", init);
	// in case the script loads after app_ready already fired
	$(() => setTimeout(init, 0));
})();
