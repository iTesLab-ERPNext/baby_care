from . import __version__ as app_version  # noqa: F401

app_name = "baby_care"
app_title = "Baby Care Management"
app_publisher = "Baby Care"
app_description = "Nursery, Daycare & Childcare Management for ERPNext v15/v16"
app_email = "admin@babycare.example"
app_license = "MIT"

required_apps = ["frappe", "erpnext"]

# Apps screen (/apps) and, on Frappe v16, the desktop icon grid
add_to_apps_screen = [
    {
        "name": "baby_care",
        "logo": "/assets/baby_care/images/baby_care_logo.svg",
        "title": "Baby Care",
        "route": "/app/baby-care-management",
        "has_permission": "baby_care.baby_care_management.utils.permissions.has_app_permission",
    }
]

# ── Install / migrate ────────────────────────────────────────────────────────
# after_install + after_migrate rebuild the desk assets (workspace, dashboard,
# number cards, charts), custom fields on Sales Invoice and the initial ERPNext
# DocType permissions. Each step is idempotent and never overwrites records or
# permissions an administrator has customised.
after_install = "baby_care.baby_care_management.setup.install.after_install"
after_migrate = "baby_care.baby_care_management.setup.install.after_migrate"
before_uninstall = "baby_care.baby_care_management.setup.install.before_uninstall"

# ── Fixtures (exported with `bench export-fixtures`) ─────────────────────────
fixtures = [
    {
        "dt": "Role",
        "filters": [["name", "in", [
            "Nursery Administrator", "Nursery Accountant",
            "Nursery Teacher", "Nursery Medical Staff", "Nursery Receptionist",
        ]]],
    },
]

# ── DocType events ───────────────────────────────────────────────────────────
doc_events = {
    "Sales Invoice": {
        "on_submit": "baby_care.baby_care_management.utils.billing.on_sales_invoice_change",
        "on_cancel": "baby_care.baby_care_management.utils.billing.on_sales_invoice_change",
        "on_update_after_submit": "baby_care.baby_care_management.utils.billing.on_sales_invoice_change",
    },
    "Payment Entry": {
        "on_submit": "baby_care.baby_care_management.utils.billing.on_payment_entry_change",
        "on_cancel": "baby_care.baby_care_management.utils.billing.on_payment_entry_change",
    },
}

# ── Scheduled tasks ──────────────────────────────────────────────────────────
scheduler_events = {
    "daily": [
        "baby_care.baby_care_management.utils.scheduler.daily_tasks",
        "baby_care.baby_care_management.utils.scheduler.generate_due_invoices",
    ],
}

# ── Boot session ─────────────────────────────────────────────────────────────
boot_session = "baby_care.baby_care_management.utils.boot.boot_session"

# ── Client scripts bundled with standard DocTypes ────────────────────────────
doctype_js = {
    "Customer": "public/js/customer_extension.js",
}

# ── Row-level permissions (server side) ──────────────────────────────────────
_perm = "baby_care.baby_care_management.utils.permissions."

permission_query_conditions = {
    "Child": _perm + "get_child_access_conditions",
    "Child Attendance": _perm + "get_attendance_conditions",
    "Child Meal Plan": _perm + "get_child_meal_plan_conditions",
    "Child Transportation": _perm + "get_child_transportation_conditions",
    "Child Service Assignment": _perm + "get_child_service_conditions",
    "Medical Record": _perm + "get_medical_record_access_conditions",
    "Health Incident": _perm + "get_health_incident_conditions",
    "Child Document": _perm + "get_child_document_conditions",
}

has_permission = {
    "Child": _perm + "has_child_permission",
    "Child Attendance": _perm + "has_attendance_permission",
    "Child Meal Plan": _perm + "has_child_meal_plan_permission",
    "Child Transportation": _perm + "has_child_transportation_permission",
    "Child Service Assignment": _perm + "has_child_service_permission",
    "Medical Record": _perm + "has_medical_record_permission",
    "Health Incident": _perm + "has_health_incident_permission",
    "Child Document": _perm + "has_child_document_permission",
}

website_route_rules = []
app_include_css = []
app_include_js = []
