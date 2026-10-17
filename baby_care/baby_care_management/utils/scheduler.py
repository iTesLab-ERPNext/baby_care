"""
Daily jobs:
* subscription lifecycle (pending → active, expiry, auto-renew)
* invoice generation for due subscriptions
* reminders: expiring subscriptions, expiring / missing documents,
  overdue nursery invoices, upcoming birthdays
Each reminder is de-duplicated per recipient and document.
"""
import frappe
from frappe import _
from frappe.utils import add_days, cint, formatdate, getdate, today

from baby_care.baby_care_management.utils.notifications import notify_roles

ADMIN = ["Nursery Administrator"]
FINANCE = ["Nursery Administrator", "Nursery Accountant"]


def _settings():
    return frappe.get_single("Nursery Settings")


def _safe(fn, *args):
    try:
        fn(*args)
        frappe.db.commit()
    except Exception:
        frappe.db.rollback()
        frappe.log_error(title=f"Baby Care: {fn.__name__} failed")


def daily_tasks():
    s = _settings()
    for job in (update_subscription_lifecycle, remind_expiring_subscriptions, update_document_status,
                remind_expiring_documents, remind_missing_documents, remind_overdue_invoices, remind_birthdays):
        _safe(job, s)


# ── subscriptions ────────────────────────────────────────────────────────────
def update_subscription_lifecycle(s=None):
    for name in frappe.get_all("Child Subscription", filters={"docstatus": 1, "status": "Pending", "start_date": ("<=", today())}, pluck="name"):
        doc = frappe.get_doc("Child Subscription", name)
        doc.status = "Active"
        doc.save(ignore_permissions=True)

    ended = frappe.get_all(
        "Child Subscription",
        filters={"docstatus": 1, "status": ("in", ["Active", "Suspended"]), "end_date": ("<", today())},
        fields=["name", "subscription_plan"],
    )
    for row in ended:
        doc = frappe.get_doc("Child Subscription", row.name)
        renewal = frappe.db.get_value("Subscription Plan", row.subscription_plan, "renewal_type")
        if renewal == "Auto-Renew" and doc.status == "Active":
            doc.flags.ignore_permissions = True
            doc.renew()
        else:
            doc.status = "Expired"
            doc.save(ignore_permissions=True)
            notify_roles(ADMIN, _("Subscription expired — {0}").format(doc.child), _("{0} ended on {1}.").format(doc.name, doc.end_date), doc.doctype, doc.name)


def generate_due_invoices(s=None):
    s = s or _settings()
    if not cint(s.auto_generate_invoices):
        return
    from baby_care.baby_care_management.utils.billing import create_subscription_invoice

    horizon = add_days(today(), cint(s.invoice_generation_day))
    due = frappe.get_all(
        "Child Subscription",
        filters={"docstatus": 1, "status": "Active", "next_billing_date": ("<=", horizon)},
        fields=["name", "next_billing_date", "end_date"],
    )
    for sub in due:
        if sub.end_date and getdate(sub.next_billing_date) > getdate(sub.end_date):
            continue
        try:
            create_subscription_invoice(sub.name)
            frappe.db.commit()
        except Exception:
            frappe.db.rollback()
            frappe.log_error(title=f"Baby Care: invoice generation failed for {sub.name}")


def remind_expiring_subscriptions(s):
    horizon = add_days(today(), cint(s.notify_subscription_expiry_days) or 14)
    for sub in frappe.get_all(
        "Child Subscription",
        filters={"docstatus": 1, "status": "Active", "end_date": ("between", [today(), horizon])},
        fields=["name", "child", "end_date"],
    ):
        notify_roles(ADMIN, _("Subscription expiring soon — {0}").format(sub.child),
                     _("{0} expires on {1}.").format(sub.name, formatdate(sub.end_date)), "Child Subscription", sub.name)


# ── documents ────────────────────────────────────────────────────────────────
def update_document_status(s=None):
    for name in frappe.get_all("Child Document", filters={"status": "Valid", "expiry_date": ("<", today())}, pluck="name"):
        frappe.db.set_value("Child Document", name, "status", "Expired")


def remind_expiring_documents(s):
    horizon = add_days(today(), cint(s.notify_document_expiry_days) or 30)
    for d in frappe.get_all(
        "Child Document",
        filters={"status": "Valid", "expiry_date": ("between", [today(), horizon])},
        fields=["name", "child", "parent_customer", "document_type", "expiry_date"],
    ):
        owner = d.child or d.parent_customer
        notify_roles(ADMIN, _("Document expiring — {0}").format(owner),
                     _("{0} expires on {1}.").format(d.document_type, formatdate(d.expiry_date)), "Child Document", d.name)


def remind_missing_documents(s):
    from baby_care.baby_care_management.doctype.child_document.child_document import get_missing_mandatory_documents

    missing = {}
    for child, doc_type in get_missing_mandatory_documents():
        missing.setdefault(child, []).append(doc_type)
    for child, types in missing.items():
        notify_roles(ADMIN, _("Missing documents — {0}").format(child), ", ".join(types), "Child", child, dedupe_days=7)


# ── finance ──────────────────────────────────────────────────────────────────
def remind_overdue_invoices(s):
    threshold = add_days(today(), -(cint(s.notify_overdue_after_days) or 0))
    for si in frappe.get_all(
        "Sales Invoice",
        filters={"docstatus": 1, "outstanding_amount": (">", 0), "due_date": ("<", threshold), "baby_care_subscription": ("is", "set")},
        fields=["name", "customer", "outstanding_amount", "due_date"],
    ):
        notify_roles(FINANCE, _("Overdue invoice — {0}").format(si.customer),
                     _("{0}: {1} outstanding since {2}.").format(si.name, si.outstanding_amount, formatdate(si.due_date)),
                     "Sales Invoice", si.name, dedupe_days=7)


# ── birthdays ────────────────────────────────────────────────────────────────
def remind_birthdays(s=None, days=7):
    t = getdate(today())
    for c in frappe.get_all("Child", filters={"enrollment_status": "Active", "date_of_birth": ("is", "set")}, fields=["name", "full_name", "date_of_birth"]):
        dob = getdate(c.date_of_birth)
        try:
            bday = dob.replace(year=t.year)
        except ValueError:  # 29 February
            bday = dob.replace(year=t.year, day=28)
        if bday < t:
            continue
        if (bday - t).days <= days:
            notify_roles(ADMIN + ["Nursery Teacher"], _("Upcoming birthday — {0}").format(c.full_name),
                         _("{0} turns {1} on {2}.").format(c.full_name, t.year - dob.year, formatdate(bday)), "Child", c.name, dedupe_days=30)


# Backwards compatibility with the old hook name
def generate_monthly_invoices():
    generate_due_invoices()
