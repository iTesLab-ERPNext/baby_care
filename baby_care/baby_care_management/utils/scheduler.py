"""
baby_care.baby_care_management.utils.scheduler
Scheduled jobs: daily tasks & monthly invoice generation.
"""
import frappe
from frappe.utils import today, getdate, add_days, nowdate


def daily_tasks():
    """Run every day: subscription expiry alerts, document expiry alerts, overdue invoices."""
    _check_subscription_expiry()
    _check_document_expiry()
    _update_overdue_invoices()
    _check_upcoming_birthdays()


def generate_monthly_invoices():
    """Run monthly: auto-generate invoices for active subscriptions."""
    settings = frappe.get_single("Nursery Settings")
    if not settings.auto_generate_invoices:
        return

    today_day = getdate(today()).day
    gen_day = int(settings.invoice_generation_day or 1)
    if today_day != gen_day:
        return

    active_subs = frappe.get_all(
        "Child Subscription",
        filters={"status": "Active", "docstatus": 1, "next_billing_date": ("<=", today())},
        fields=["name"],
    )
    for sub in active_subs:
        try:
            from baby_care.baby_care_management.utils.billing import create_subscription_invoice
            create_subscription_invoice(sub.name)
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"Failed to generate invoice for {sub.name}",
            )


def _check_subscription_expiry():
    settings = frappe.get_single("Nursery Settings")
    days_ahead = int(settings.notify_subscription_expiry_days or 14)
    threshold = add_days(today(), days_ahead)

    expiring = frappe.get_all(
        "Child Subscription",
        filters={
            "status": "Active",
            "docstatus": 1,
            "end_date": ("between", [today(), threshold]),
        },
        fields=["name", "child", "end_date"],
    )
    for sub in expiring:
        _send_notification(
            subject=f"Subscription expiring soon — {sub.child}",
            message=f"Subscription {sub.name} for child {sub.child} expires on {sub.end_date}.",
            doctype="Child Subscription",
            docname=sub.name,
        )


def _check_document_expiry():
    settings = frappe.get_single("Nursery Settings")
    days_ahead = int(settings.notify_document_expiry_days or 30)
    threshold = add_days(today(), days_ahead)

    expiring_docs = frappe.get_all(
        "Child Document",
        filters={
            "status": "Valid",
            "expiry_date": ("between", [today(), threshold]),
        },
        fields=["name", "child", "document_type", "expiry_date"],
    )
    for doc in expiring_docs:
        _send_notification(
            subject=f"Document expiring — {doc.child}",
            message=(
                f"Document '{doc.document_type}' for {doc.child} "
                f"expires on {doc.expiry_date}."
            ),
            doctype="Child Document",
            docname=doc.name,
        )


def _update_overdue_invoices():
    settings = frappe.get_single("Nursery Settings")
    overdue_days = int(settings.notify_overdue_after_days or 7)
    threshold = add_days(today(), -overdue_days)

    overdue_sis = frappe.get_all(
        "Sales Invoice",
        filters={
            "docstatus": 1,
            "outstanding_amount": (">", 0),
            "due_date": ("<", threshold),
            "status": ("!=", "Paid"),
        },
        fields=["name"],
    )
    for si in overdue_sis:
        frappe.db.set_value("Sales Invoice", si.name, "status", "Overdue", update_modified=False)


def _check_upcoming_birthdays():
    from frappe.utils import formatdate
    import datetime
    today_date = getdate(today())
    window = add_days(today(), 7)
    children = frappe.get_all(
        "Child",
        filters={"enrollment_status": "Active"},
        fields=["name", "full_name", "date_of_birth"],
    )
    for child in children:
        if not child.date_of_birth:
            continue
        dob = getdate(child.date_of_birth)
        # birthday this year
        try:
            birthday_this_year = dob.replace(year=today_date.year)
        except ValueError:
            continue
        if today_date <= birthday_this_year <= getdate(window):
            _send_notification(
                subject=f"Upcoming birthday — {child.full_name}",
                message=f"{child.full_name}'s birthday is on {formatdate(birthday_this_year)}.",
                doctype="Child",
                docname=child.name,
            )


def _send_notification(subject, message, doctype, docname):
    admins = frappe.get_all(
        "Has Role",
        filters={"role": "Nursery Administrator", "parenttype": "User"},
        fields=["parent"],
    )
    for admin in admins:
        if not frappe.db.get_value("User", admin.parent, "enabled"):
            continue
        notification = frappe.new_doc("Notification Log")
        notification.subject = subject
        notification.email_content = message
        notification.document_type = doctype
        notification.document_name = docname
        notification.for_user = admin.parent
        notification.type = "Alert"
        notification.insert(ignore_permissions=True)
