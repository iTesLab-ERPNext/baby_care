"""
Desk assets: Number Cards, Dashboard Charts, the Baby Care Dashboard and the
"Baby Care Management" workspace (/app/baby-care-management).

Frappe v15 workspace schema (verified against frappe/desk/doctype):
* Workspace Link: ``type`` is "Link" or "Card Break"; the target kind goes in
  ``link_type`` ("DocType" | "Page" | "Report"). Links without ``link_type``
  are dropped by the desk, which is what produced empty cards before.
* Script / Query reports need ``is_query_report = 1``.
* ``content`` is a JSON list of blocks; ``card`` blocks reference Card Break
  labels, ``shortcut`` blocks shortcut labels, ``number_card`` / ``chart``
  blocks the rows of ``number_cards`` / ``charts``.
"""
import json

import frappe

MODULE = "Baby Care Management"
WORKSPACE = "Baby Care Management"
DASHBOARD = "Baby Care Dashboard"
API = "baby_care.baby_care_management.api.dashboard."

WORKSPACE_ROLES = [
    "System Manager",
    "Nursery Administrator",
    "Nursery Accountant",
    "Nursery Teacher",
    "Nursery Medical Staff",
    "Nursery Receptionist",
]

# label, method, color
NUMBER_CARDS = [
    ("Enrolled Children", "enrolled_children", "#2490EF"),
    ("Active Parents", "active_parents", "#7575FF"),
    ("Present Today", "present_today", "#29CD42"),
    ("Absent Today", "absent_today", "#E24C4C"),
    ("Active Subscriptions", "active_subscriptions", "#5E64FF"),
    ("Subscriptions Expiring Soon", "expiring_subscriptions", "#FF8D25"),
    ("Monthly Revenue", "monthly_revenue", "#29CD42"),
    ("Quarterly Revenue", "quarterly_revenue", "#29CD42"),
    ("Outstanding Payments", "outstanding_payments", "#E24C4C"),
    ("Overdue Invoices", "overdue_invoices", "#E24C4C"),
    ("Active Teachers", "active_teachers", "#2490EF"),
    ("Missing or Expired Documents", "missing_documents", "#FF8D25"),
    ("Upcoming Birthdays", "upcoming_birthdays", "#ECAD4B"),
]
WORKSPACE_CARDS = [
    "Enrolled Children", "Present Today", "Absent Today", "Active Subscriptions",
    "Subscriptions Expiring Soon", "Monthly Revenue", "Outstanding Payments", "Missing or Expired Documents",
]


def _charts():
    return [
        {
            "chart_name": "Children by Class",
            "chart_type": "Group By",
            "document_type": "Child",
            "group_by_type": "Count",
            "group_by_based_on": "nursery_class",
            "type": "Bar",
            "filters_json": json.dumps([["Child", "enrollment_status", "=", "Active", False]]),
            "color": "#2490EF",
        },
        {
            "chart_name": "Children by Age Group",
            "chart_type": "Group By",
            "document_type": "Child",
            "group_by_type": "Count",
            "group_by_based_on": "age_group",
            "type": "Donut",
            "filters_json": json.dumps([["Child", "enrollment_status", "=", "Active", False]]),
        },
        {
            "chart_name": "Daily Attendance",
            "chart_type": "Count",
            "document_type": "Child Attendance",
            "based_on": "attendance_date",
            "timeseries": 1,
            "timespan": "Last Month",
            "time_interval": "Daily",
            "type": "Line",
            "filters_json": "[]",
            "color": "#29CD42",
        },
        {
            "chart_name": "Nursery Revenue",
            "chart_type": "Sum",
            "document_type": "Sales Invoice",
            "based_on": "posting_date",
            "value_based_on": "base_grand_total",
            "timeseries": 1,
            "timespan": "Last Year",
            "time_interval": "Monthly",
            "type": "Bar",
            "filters_json": json.dumps([
                ["Sales Invoice", "docstatus", "=", 1, False],
                ["Sales Invoice", "baby_care_subscription", "is", "set", False],
            ]),
            "color": "#5E64FF",
        },
        {
            "chart_name": "Subscriptions by Status",
            "chart_type": "Group By",
            "document_type": "Child Subscription",
            "group_by_type": "Count",
            "group_by_based_on": "status",
            "type": "Pie",
            "filters_json": json.dumps([["Child Subscription", "docstatus", "<", 2, False]]),
        },
    ]


WORKSPACE_CHARTS = ["Children by Class", "Daily Attendance", "Nursery Revenue", "Subscriptions by Status"]

# label, link_to, type
SHORTCUTS = [
    ("Baby Care Dashboard", DASHBOARD, "Dashboard"),
    ("Children", "Child", "DocType"),
    ("Parents", "Customer", "DocType"),
    ("Attendance", "Child Attendance", "DocType"),
    ("Subscriptions", "Child Subscription", "DocType"),
    ("Medical Records", "Medical Record", "DocType"),
    ("Sales Invoices", "Sales Invoice", "DocType"),
    ("Data Management", "baby-care-data", "Page"),
]

D, R, P = "DocType", "Report", "Page"
# Card title -> [(label, link_to, link_type)]
SECTIONS = [
    ("Dashboard", [
        ("Overview and Statistics", "Enrolled Children Summary", R),
        ("Attendance Overview", "Attendance Summary", R),
        ("Financial Overview", "Revenue Report", R),
    ]),
    ("Parents & Children", [
        ("Parents (Customer)", "Customer", D),
        ("Children", "Child", D),
        ("Enrollment", "Enrolled Children Summary", R),
        ("Classes & Groups", "Nursery Class", D),
        ("Teacher Assignments", "Teacher Profile", D),
        ("Age Groups", "Age Group", D),
    ]),
    ("Subscriptions & Billing", [
        ("Subscription Plans", "Subscription Plan", D),
        ("Child Subscriptions", "Child Subscription", D),
        ("Sales Invoices", "Sales Invoice", D),
        ("Payment Entries", "Payment Entry", D),
        ("Outstanding Payments", "Outstanding Payments", R),
        ("Parent Account Statement", "Parent Account Statement", R),
    ]),
    ("Health & Documents", [
        ("Child Medical Records", "Medical Record", D),
        ("Health Incidents", "Health Incident", D),
        ("Vaccination Records", "Vaccination Status", R),
        ("Child & Parent Documents", "Child Document", D),
        ("Document Alerts", "Medical and Document Alerts", R),
    ]),
    ("Services & Activities", [
        ("Services & Activities", "Nursery Service", D),
        ("Child-Specific Services", "Child Service Assignment", D),
        ("Meal Plans", "Meal Plan", D),
        ("Child Meal Plans", "Child Meal Plan", D),
        ("Daily Meal List", "Daily Meal List", R),
        ("Transportation Routes", "Transportation Route", D),
        ("Child Transportation", "Child Transportation", D),
    ]),
    ("Staff & Attendance", [
        ("Teachers", "Teacher Profile", D),
        ("Staff Management", "Employee", D),
        ("Child Attendance", "Child Attendance", D),
        ("Daily Attendance Report", "Attendance Summary", R),
    ]),
    ("Reports", [
        ("Children Report", "Enrolled Children Summary", R),
        ("Parents Report", "Parent Account Statement", R),
        ("Subscription Report", "Subscription Status Report", R),
        ("Revenue Report", "Revenue Report", R),
        ("Outstanding Payments", "Outstanding Payments", R),
        ("Attendance Report", "Attendance Summary", R),
        ("Medical and Document Alerts", "Medical and Document Alerts", R),
        ("Vaccination Status", "Vaccination Status", R),
    ]),
    ("Configuration", [
        ("Application Settings", "Nursery Settings", D),
        ("Subscription Configuration", "Subscription Plan", D),
        ("Services Configuration", "Service Category", D),
        ("Meal Configuration", "Meal Category", D),
        ("Transportation Configuration", "Transportation Route", D),
        ("Classes", "Nursery Class", D),
        ("Age Groups", "Age Group", D),
        ("Document Types", "Document Type Config", D),
        ("Attendance Statuses", "Attendance Status", D),
        ("Role Permissions Manager", "permission-manager", P),
        ("User Permissions", "User Permission", D),
    ]),
    ("Data Management", [
        ("Seed Data Management", "baby-care-data", P),
    ]),
]


# ── public entry points ──────────────────────────────────────────────────────
def sync_desk():
    for label, method, color in NUMBER_CARDS:
        ensure_number_card(label, method, color)
    for chart in _charts():
        ensure_chart(chart)
    fix_currencies()
    ensure_dashboard()
    build_workspace()


MONEY_CARDS = {"Monthly Revenue", "Quarterly Revenue", "Outstanding Payments"}
MONEY_CHARTS = {"Nursery Revenue"}


def _company_currency():
    company = frappe.db.get_single_value("Nursery Settings", "default_company") or frappe.defaults.get_global_default("company")
    return frappe.get_cached_value("Company", company, "default_currency") if company else None


def fix_currencies():
    """Frappe fills the empty `currency` link of new Number Cards / Dashboard
    Charts from the site default, which makes count widgets render as money.
    Counts get no currency; money widgets get the company currency."""
    currency = _company_currency()
    for label, _method, _color in NUMBER_CARDS:
        if frappe.db.exists("Number Card", label):
            frappe.db.set_value("Number Card", label, "currency", currency if label in MONEY_CARDS else None, update_modified=False)
    for chart in _charts():
        name = chart["chart_name"]
        if frappe.db.exists("Dashboard Chart", name):
            frappe.db.set_value("Dashboard Chart", name, "currency", currency if name in MONEY_CHARTS else None, update_modified=False)


def remove_desk():
    for dt, names in (
        ("Workspace", [WORKSPACE]),
        ("Dashboard", [DASHBOARD]),
        ("Dashboard Chart", [c["chart_name"] for c in _charts()]),
        ("Number Card", [c[0] for c in NUMBER_CARDS]),
    ):
        for name in names:
            if frappe.db.exists(dt, name):
                frappe.delete_doc(dt, name, ignore_permissions=True, force=True)


# ── builders ─────────────────────────────────────────────────────────────────
def ensure_number_card(label, method, color):
    if frappe.db.exists("Number Card", label):
        return
    doc = frappe.get_doc({
        "doctype": "Number Card",
        "name": label,
        "label": label,
        "type": "Custom",
        "method": API + method,
        "is_public": 1,
        "is_standard": 0,
        "module": MODULE,
        "color": color,
        "show_percentage_stats": 0,
        "filters_json": "[]",
    })
    doc.insert(ignore_permissions=True)


def ensure_chart(chart):
    if frappe.db.exists("Dashboard Chart", chart["chart_name"]):
        return
    if not frappe.db.exists("DocType", chart["document_type"]):
        return
    frappe.get_doc(dict({
        "doctype": "Dashboard Chart",
        "is_public": 1,
        "is_standard": 0,
        "module": MODULE,
        "timeseries": 0,
        "number_of_groups": 0,
    }, **chart)).insert(ignore_permissions=True)


def ensure_dashboard():
    if frappe.db.exists("Dashboard", DASHBOARD):
        return
    frappe.get_doc({
        "doctype": "Dashboard",
        "dashboard_name": DASHBOARD,
        "is_standard": 0,
        "module": MODULE,
        "cards": [{"card": c[0]} for c in NUMBER_CARDS if frappe.db.exists("Number Card", c[0])],
        "charts": [
            {"chart": c["chart_name"], "width": "Full" if c["chart_name"] in ("Daily Attendance", "Nursery Revenue") else "Half"}
            for c in _charts() if frappe.db.exists("Dashboard Chart", c["chart_name"])
        ],
    }).insert(ignore_permissions=True)


def _target_exists(link_to, link_type):
    if link_type == "DocType":
        meta = frappe.db.get_value("DocType", link_to, ["istable"], as_dict=True)
        return bool(meta) and not meta.istable
    if link_type == "Report":
        return bool(frappe.db.exists("Report", {"name": link_to, "disabled": 0}))
    if link_type == "Page":
        return bool(frappe.db.exists("Page", link_to))
    if link_type == "Dashboard":
        return bool(frappe.db.exists("Dashboard", link_to))
    return False


def _report_meta(name):
    return frappe.db.get_value("Report", name, ["report_type", "ref_doctype"], as_dict=True) or {}


def _block(kind, data):
    return {"id": frappe.generate_hash(length=10), "type": kind, "data": data}


def _header(text):
    return _block("header", {"text": f'<span class="h4"><b>{text}</b></span>', "col": 12})


def build_workspace():
    links, card_names, skipped = [], [], []
    for title, items in SECTIONS:
        rows = []
        for label, link_to, link_type in items:
            if not _target_exists(link_to, link_type):
                skipped.append(f"{title} → {link_to}")
                continue
            row = {"type": "Link", "label": label, "link_type": link_type, "link_to": link_to, "onboard": 0, "hidden": 0}
            if link_type == "Report":
                meta = _report_meta(link_to)
                row["is_query_report"] = 1 if meta.get("report_type") in ("Script Report", "Query Report") else 0
                row["report_ref_doctype"] = meta.get("ref_doctype")
            rows.append(row)
        if not rows:
            continue
        links.append({"type": "Card Break", "label": title, "link_count": len(rows), "hidden": 0})
        links.extend(rows)
        card_names.append(title)

    shortcuts = [
        {"type": t, "label": label, "link_to": link_to, **({"doc_view": "List"} if t == "DocType" else {})}
        for label, link_to, t in SHORTCUTS
        if _target_exists(link_to, t)
    ]
    cards = [c for c in WORKSPACE_CARDS if frappe.db.exists("Number Card", c)]
    charts = [c for c in WORKSPACE_CHARTS if frappe.db.exists("Dashboard Chart", c)]

    content = [_header("Overview")]
    content += [_block("number_card", {"number_card_name": c, "col": 3}) for c in cards]
    content += [_block("chart", {"chart_name": c, "col": 6}) for c in charts]
    content += [_block("spacer", {"col": 12}), _header("Quick Access")]
    content += [_block("shortcut", {"shortcut_name": s["label"], "col": 3}) for s in shortcuts]
    content += [_block("spacer", {"col": 12}), _header("Modules")]
    content += [_block("card", {"card_name": c, "col": 4}) for c in card_names]

    if frappe.db.exists("Workspace", WORKSPACE):
        frappe.delete_doc("Workspace", WORKSPACE, ignore_permissions=True, force=True)

    ws = frappe.get_doc({
        "doctype": "Workspace",
        "name": WORKSPACE,
        "label": WORKSPACE,
        "title": WORKSPACE,
        "module": MODULE,
        "icon": "users",
        "indicator_color": "blue",
        "public": 1,
        "is_hidden": 0,
        "hide_custom": 0,
        "sequence_id": 30,
        "content": json.dumps(content),
        "links": links,
        "shortcuts": shortcuts,
        "number_cards": [{"number_card_name": c, "label": c} for c in cards],
        "charts": [{"chart_name": c, "label": c} for c in charts],
        "roles": [{"role": r} for r in WORKSPACE_ROLES if frappe.db.exists("Role", r)],
    })
    if ws.meta.has_field("type"):  # Frappe v16
        ws.type = "Workspace"
    ws.insert(ignore_permissions=True)
    if skipped:
        print("Baby Care workspace: skipped links to missing targets: " + "; ".join(skipped))
    return ws.name
