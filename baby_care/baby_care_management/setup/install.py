"""
Install / migrate entry points.

Runs on ``after_install`` and on every ``after_migrate``. Each step is
idempotent:

* roles and master data are created only when missing;
* number cards, charts and the dashboard are created only when missing;
* the workspace is rebuilt from ``desk.py`` so navigation always matches the
  installed version of the app;
* sites upgraded from 1.x (which ran on ERPNext) lose the app's old custom
  fields on ERPNext DocTypes — 2.0 keeps everything in its own DocTypes.

The app needs the Frappe Framework only. Users and roles are Frappe's own.
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

# Custom fields 1.x added to ERPNext DocTypes; removed on migrate to 2.0.
LEGACY_CUSTOM_FIELDS = {
    "Customer": ["bc_parent_app_tab", "bc_parent_app_access", "bc_parent_login", "bc_parent_password",
                 "bc_send_credentials", "bc_parent_app_col", "bc_parent_user"],
    "Sales Invoice": ["baby_care_section", "baby_care_child", "baby_care_subscription", "baby_care_billing_period"],
}


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
    steps = (ensure_roles, remove_legacy_custom_fields, ensure_master_data, desk.sync_desk)
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


# Parents use the website / Parent API only: no desk access.
PORTAL_ROLES = ["Nursery Parent"]


def ensure_roles():
    for role in ROLES + PORTAL_ROLES:
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 0 if role in PORTAL_ROLES else 1}).insert(ignore_permissions=True)


def remove_legacy_custom_fields():
    for doctype, fields in LEGACY_CUSTOM_FIELDS.items():
        for fieldname in fields:
            name = f"{doctype}-{fieldname}"
            if frappe.db.exists("Custom Field", name):
                frappe.delete_doc("Custom Field", name, ignore_permissions=True, force=True)


def ensure_master_data():
    from baby_care.baby_care_management.api.seed import install_master_data

    install_master_data()


def before_uninstall():
    from baby_care.baby_care_management.api.seed import _clear_tracked

    try:
        _clear_tracked()
    except Exception:
        frappe.log_error(title="Baby Care: could not clear test data on uninstall")
    remove_legacy_custom_fields()
    desk.remove_desk()
