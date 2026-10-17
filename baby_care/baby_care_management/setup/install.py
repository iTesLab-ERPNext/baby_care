"""
Install / migrate entry points.

Runs on ``after_install`` and on every ``after_migrate``. Each step is
idempotent:

* roles, custom fields and master data are created only when missing;
* ERPNext DocType permissions for nursery roles are added only if the role
  has no permission rule on that DocType yet (so edits made in Role
  Permissions Manager are never overwritten);
* number cards, charts and the dashboard are created only when missing;
* the workspace is rebuilt from ``desk.py`` so navigation always matches the
  installed version of the app.
"""
import frappe

from baby_care.baby_care_management.setup import desk

ROLES = [
    "Nursery Administrator",
    "Nursery Accountant",
    "Nursery Teacher",
    "Nursery Medical Staff",
    "Nursery Receptionist",
]

SALES_INVOICE_FIELDS = [
    {"fieldname": "baby_care_section", "fieldtype": "Section Break", "label": "Baby Care", "insert_after": "remarks", "collapsible": 1},
    {"fieldname": "baby_care_child", "fieldtype": "Link", "label": "Child", "options": "Child", "insert_after": "baby_care_section", "read_only": 1, "in_standard_filter": 1},
    {"fieldname": "baby_care_subscription", "fieldtype": "Link", "label": "Child Subscription", "options": "Child Subscription", "insert_after": "baby_care_child", "read_only": 1, "search_index": 1},
    {"fieldname": "baby_care_billing_period", "fieldtype": "Data", "label": "Billing Period", "insert_after": "baby_care_subscription", "read_only": 1},
]

# (DocType, role, permissions) for standard ERPNext DocTypes the nursery
# roles need. Users still need ERPNext's own roles (e.g. Accounts User,
# Sales User) to open every linked master — see README.
_FULL_TX = ["read", "write", "create", "submit", "cancel", "amend", "report", "export", "print", "email", "share"]
ERPNEXT_PERMISSIONS = [
    ("Customer", "System Manager", ["read", "write", "create", "delete", "report", "export", "print", "email", "share"]),
    ("Sales Invoice", "System Manager", _FULL_TX),
    ("Payment Entry", "System Manager", _FULL_TX),
    ("Customer", "Nursery Administrator", ["read", "write", "create", "report", "export", "print", "email", "share"]),
    ("Customer", "Nursery Receptionist", ["read", "write", "create", "report", "print", "email"]),
    ("Customer", "Nursery Accountant", ["read", "report", "print", "email"]),
    ("Sales Invoice", "Nursery Administrator", ["read", "write", "create", "submit", "cancel", "amend", "report", "export", "print", "email"]),
    ("Sales Invoice", "Nursery Accountant", ["read", "write", "create", "submit", "cancel", "amend", "report", "export", "print", "email"]),
    ("Payment Entry", "Nursery Administrator", ["read", "write", "create", "submit", "cancel", "amend", "report", "export", "print", "email"]),
    ("Payment Entry", "Nursery Accountant", ["read", "write", "create", "submit", "cancel", "amend", "report", "export", "print", "email"]),
]


def after_install():
    _refresh_module_map()
    run_setup()


def after_migrate():
    run_setup()


def _refresh_module_map():
    """install-app caches the module→app map before this app is registered;
    rebuild it so this app's DocType controllers can be imported."""
    for key in ("app_modules", "module_app", "installed_app_modules"):
        frappe.cache.delete_value(key)
    frappe.local.app_modules = None
    frappe.local.module_app = None
    frappe.setup_module_map()
    frappe.clear_cache()


def run_setup():
    """Run each step inside a savepoint.

    Never call frappe.db.rollback() here: during install-app the DocType sync
    of this very app is still uncommitted and a full rollback would erase it.
    """
    steps = (ensure_roles, ensure_custom_fields, ensure_master_data, ensure_erpnext_permissions, desk.sync_desk)
    for step in steps:
        sp = f"baby_care_{step.__name__}"
        frappe.db.savepoint(sp)
        try:
            step()
            _quiet(frappe.db.release_savepoint, sp)  # DDL may have committed implicitly
        except Exception:
            _quiet(frappe.db.rollback, save_point=sp)
            frappe.log_error(title=f"Baby Care setup step failed: {step.__name__}")
            print(f"Baby Care: setup step {step.__name__} failed — see Error Log")
            if frappe.flags.in_test:
                raise


def _quiet(fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except Exception:
        pass


def ensure_roles():
    for role in ROLES:
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(ignore_permissions=True)


def ensure_custom_fields():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    create_custom_fields({"Sales Invoice": SALES_INVOICE_FIELDS}, ignore_validate=True, update=True)


def ensure_master_data():
    from baby_care.baby_care_management.api.seed import install_master_data

    install_master_data()


def ensure_erpnext_permissions():
    from frappe.permissions import add_permission, update_permission_property

    for doctype, role, ptypes in ERPNEXT_PERMISSIONS:
        if not frappe.db.exists("DocType", doctype):
            continue
        has_rule = frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role}) or (
            not frappe.db.exists("Custom DocPerm", {"parent": doctype})
            and frappe.db.exists("DocPerm", {"parent": doctype, "role": role})
        )
        if has_rule:
            continue
        add_permission(doctype, role, 0)
        for ptype in ptypes:
            update_permission_property(doctype, role, 0, ptype, 1, validate=False)


def before_uninstall():
    from baby_care.baby_care_management.api.seed import _clear_tracked

    try:
        _clear_tracked()  # demo records also live in ERPNext tables (Customer, Sales Invoice)
    except Exception:
        frappe.log_error(title="Baby Care: could not clear test data on uninstall")
    for df in SALES_INVOICE_FIELDS:
        name = f"Sales Invoice-{df['fieldname']}"
        if frappe.db.exists("Custom Field", name):
            frappe.delete_doc("Custom Field", name, ignore_permissions=True)
    desk.remove_desk()
