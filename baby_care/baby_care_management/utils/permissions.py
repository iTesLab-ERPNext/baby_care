"""
Permission query conditions for role-based data filtering.
Used as `permission_query_conditions` in hooks.py.

System Manager and Nursery Administrator always get unrestricted access.
"""
import frappe


def _is_admin(user=None):
    """Return True if user has full administrative access."""
    if not user:
        user = frappe.session.user
    if user == "Administrator":
        return True
    roles = frappe.get_roles(user)
    return "System Manager" in roles or "Nursery Administrator" in roles


def get_child_access_conditions(user=None):
    """
    - System Manager / Nursery Administrator: no filter (see all children).
    - Nursery Teacher: only children where assigned_teacher matches their profile.
    - Nursery Receptionist: read-only access already granted via DocType perms; no row filter.
    - Everyone else: no rows returned.
    """
    if not user:
        user = frappe.session.user

    if _is_admin(user):
        return ""

    roles = frappe.get_roles(user)

    if "Nursery Teacher" in roles:
        teacher = frappe.db.get_value(
            "Teacher Profile", {"user_account": user}, "name"
        )
        if teacher:
            return f"`tabChild`.`assigned_teacher` = {frappe.db.escape(teacher)}"
        # Teacher profile not linked — show nothing
        return "1=0"

    if "Nursery Receptionist" in roles:
        # Receptionist can see all children (read-only enforced by DocType perms)
        return ""

    # All other roles: deny at row level
    return "1=0"


def get_medical_record_access_conditions(user=None):
    """
    Medical records are private:
    - System Manager / Nursery Administrator / Nursery Medical Staff: unrestricted.
    - Everyone else: no rows.
    """
    if not user:
        user = frappe.session.user

    if _is_admin(user):
        return ""

    roles = frappe.get_roles(user)
    if "Nursery Medical Staff" in roles:
        return ""

    return "1=0"
