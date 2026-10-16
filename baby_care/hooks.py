from . import __version__ as app_version

app_name = "baby_care"
app_title = "Baby Care Management"
app_publisher = "Baby Care"
app_description = "Nursery, Daycare & Childcare Management for ERPNext v15/v16"
app_email = "admin@babycare.example"
app_license = "MIT"

required_apps = ["frappe", "erpnext"]

# ── Fixtures ────────────────────────────────────────────────────────────────
fixtures = [
    {
        "dt": "Role",
        "filters": [["name", "in", [
            "Nursery Administrator", "Nursery Accountant",
            "Nursery Teacher", "Nursery Medical Staff", "Nursery Receptionist",
        ]]],
    },
    {"dt": "Age Group"},
    {"dt": "Meal Category"},
    {"dt": "Service Category"},
    {"dt": "Attendance Status"},
]

# ── DocType events ──────────────────────────────────────────────────────────
doc_events = {
    "Sales Invoice": {
        "on_submit": "baby_care.baby_care_management.utils.billing.on_sales_invoice_submit",
        "on_cancel": "baby_care.baby_care_management.utils.billing.on_sales_invoice_cancel",
    },
}

# ── Scheduled tasks ─────────────────────────────────────────────────────────
scheduler_events = {
    "daily": [
        "baby_care.baby_care_management.utils.scheduler.daily_tasks",
    ],
    "monthly": [
        "baby_care.baby_care_management.utils.scheduler.generate_monthly_invoices",
    ],
}

# ── Boot session ─────────────────────────────────────────────────────────────
boot_session = "baby_care.baby_care_management.utils.boot.boot_session"

# ── Client scripts bundled with specific DocTypes ──────────────────────────
doctype_js = {
    "Customer": "public/js/customer_extension.js",
}

# ── Permission query conditions (teacher sees only own children) ────────────
permission_query_conditions = {
    "Child": "baby_care.baby_care_management.utils.permissions.get_child_access_conditions",
}

website_route_rules = []
app_include_css = []
app_include_js = []
