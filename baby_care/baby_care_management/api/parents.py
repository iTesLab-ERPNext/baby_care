"""Staff actions for parent (mobile app) accounts."""
import frappe
from frappe.utils import cint

from baby_care.baby_care_management.utils.parent_access import PARENT_ROLE, enable_access  # noqa: F401


@frappe.whitelist(methods=["POST"])
def create_parent_user(parent_profile, email=None, send_welcome_email=1, password=None):
    """Create (or reuse) the parent's app login on a Parent Profile.

    The Parent Profile form's "Parent App" tab does the same.
    """
    frappe.has_permission("Parent Profile", "write", parent_profile, throw=True)
    result = enable_access(parent_profile, password=password or None, send_email=cint(send_welcome_email), login=email)
    return {"user": result["user"], "created": result["created"], "parent_profile": parent_profile,
            "password": result.get("password_generated")}


@frappe.whitelist(methods=["GET"])
def get_parent_users(parent_profile):
    frappe.has_permission("Parent Profile", "read", parent_profile, throw=True)
    user = frappe.db.get_value("Parent Profile", parent_profile, "user")
    return [user] if user else []
