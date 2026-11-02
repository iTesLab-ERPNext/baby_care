"""Staff actions for parent (portal) accounts."""
import frappe
from frappe import _
from frappe.utils import cint, validate_email_address

PARENT_ROLE = "Nursery Parent"


@frappe.whitelist(methods=["POST"])
def create_parent_user(customer, email, first_name=None, last_name=None, send_welcome_email=1):
    """Create (or reuse) a website user for a parent and add it to the Customer's Portal Users."""
    frappe.has_permission("Customer", "write", customer, throw=True)
    email = (email or "").strip().lower()
    if not validate_email_address(email):
        frappe.throw(_("A valid e-mail address is required."))
    cust = frappe.get_doc("Customer", customer)

    if frappe.db.exists("User", email):
        user = frappe.get_doc("User", email)
        if user.user_type == "System User" and not frappe.has_permission("User", "write"):
            frappe.throw(_("{0} is a staff account; ask an administrator to link it.").format(email))
        created = False
    else:
        names = (cust.customer_name or "").split(" ", 1)
        user = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": first_name or names[0],
            "last_name": last_name or (names[1] if len(names) > 1 else ""),
            "user_type": "Website User",
            "send_welcome_email": cint(send_welcome_email),
        })
        user.flags.ignore_permissions = True
        user.insert()
        created = True
    if PARENT_ROLE not in frappe.get_roles(user.name):
        user.flags.ignore_permissions = True
        user.add_roles(PARENT_ROLE)

    if not any(p.user == user.name for p in cust.get("portal_users") or []):
        cust.append("portal_users", {"user": user.name})
        cust.flags.ignore_permissions = True
        cust.save()
    return {"user": user.name, "created": created, "customer": customer}


@frappe.whitelist(methods=["GET"])
def get_parent_users(customer):
    frappe.has_permission("Customer", "read", customer, throw=True)
    return frappe.get_all("Portal User", filters={"parent": customer, "parenttype": "Customer"}, pluck="user")
