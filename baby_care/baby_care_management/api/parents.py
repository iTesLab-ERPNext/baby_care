"""Staff actions for parent (portal / mobile app) accounts."""
import frappe
from frappe import _
from frappe.utils import cint

from baby_care.baby_care_management.utils.parent_access import PARENT_ROLE, enable_access  # noqa: F401


@frappe.whitelist(methods=["POST"])
def create_parent_user(customer, email, first_name=None, last_name=None, send_welcome_email=1, password=None):
    """Create (or reuse) the parent's app login and link it to the Customer.

    Kept for compatibility; the Customer form's "Parent App" tab does the same.
    """
    frappe.has_permission("Customer", "write", customer, throw=True)
    result = enable_access(customer, password=password or None, send_email=cint(send_welcome_email), login=email,
                           additional=True)
    return {"user": result["user"], "created": result["created"], "customer": customer,
            "password": result.get("password_generated")}


@frappe.whitelist(methods=["GET"])
def get_parent_users(customer):
    frappe.has_permission("Customer", "read", customer, throw=True)
    return frappe.get_all("Portal User", filters={"parent": customer, "parenttype": "Customer"}, pluck="user")
