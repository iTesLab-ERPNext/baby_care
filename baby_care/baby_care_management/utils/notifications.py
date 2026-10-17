"""In-app notifications (Notification Log) with de-duplication."""
import frappe
from frappe.utils import add_days, today


def users_with_roles(roles):
    users = frappe.get_all(
        "Has Role",
        filters={"role": ("in", list(roles)), "parenttype": "User", "parent": ("not in", ["Administrator", "Guest"])},
        pluck="parent",
        distinct=True,
    )
    users = [u for u in users if frappe.db.get_value("User", u, "enabled")]
    if not users:
        users = [u for u in frappe.get_all(
            "Has Role", filters={"role": "System Manager", "parenttype": "User", "parent": ("not in", ["Guest"])}, pluck="parent", distinct=True
        ) if frappe.db.get_value("User", u, "enabled")]
    return sorted(set(users))


def notify_roles(roles, subject, message, doctype, docname, dedupe_days=None):
    """Create one Notification Log per recipient.

    ``dedupe_days``: skip a recipient who already received the same subject for
    the same document within that many days (None = ever).
    """
    sent = 0
    for user in users_with_roles(roles):
        filters = {"for_user": user, "document_type": doctype, "document_name": docname, "subject": subject}
        if dedupe_days is not None:
            filters["creation"] = (">=", add_days(today(), -int(dedupe_days)))
        if frappe.db.exists("Notification Log", filters):
            continue
        frappe.get_doc({
            "doctype": "Notification Log",
            "subject": subject,
            "email_content": message,
            "document_type": doctype,
            "document_name": docname,
            "for_user": user,
            "type": "Alert",
        }).insert(ignore_permissions=True)
        sent += 1
    return sent
