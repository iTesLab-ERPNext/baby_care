"""
Permission query conditions for role-based data filtering.
Used as `permission_query_conditions` in hooks.py if desired.
"""
import frappe


def get_child_access_conditions(user=None):
    """Teachers see only children assigned to them."""
    if not user:
        user = frappe.session.user
    if "Nursery Administrator" in frappe.get_roles(user):
        return ""
    if "Nursery Teacher" in frappe.get_roles(user):
        teacher = frappe.db.get_value(
            "Teacher Profile", {"user_account": user}, "name"
        )
        if teacher:
            return f"`tabChild`.assigned_teacher = {frappe.db.escape(teacher)}"
    return ""
