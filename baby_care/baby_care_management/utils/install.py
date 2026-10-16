"""
Install / migrate helpers for Baby Care Management.

before_migrate: deletes the existing Workspace record so that the fixture
always creates a fresh, fully-populated copy during sync_fixtures().
Without this, Frappe's sync_fixtures skips existing records and the
workspace content stays stale.
"""
import frappe


def before_migrate():
    """Drop the Baby Care Management workspace so the fixture reimports it cleanly."""
    if frappe.db.exists("Workspace", "Baby Care Management"):
        frappe.db.delete("Workspace", {"name": "Baby Care Management"})
        frappe.db.commit()
