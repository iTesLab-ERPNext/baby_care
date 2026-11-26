"""
Push notifications to parents' phones (Expo push service).

Events: check-in / check-out, health incidents, new nursery invoices and
payments. Sending is queued after the transaction commits and never blocks or
fails the staff member's save. Switch off in Nursery Settings.
"""
import frappe
from frappe import _
from frappe.utils import cint, flt, fmt_money, now_datetime
from baby_care.api.v1 import _hhmm, _money

EXPO_URL = "https://exp.host/--/api/v2/push/send"


def _enabled():
    return cint(frappe.db.get_single_value("Nursery Settings", "enable_push_notifications"))


def parent_users_of_child(child):
    customers = frappe.get_all("Child Parent Link", filters={"parenttype": "Child", "parent": child}, pluck="parent_customer")
    return parent_users_of_customers(customers)


def parent_users_of_customers(customers):
    if not customers:
        return []
    users = frappe.get_all("Portal User", filters={"parenttype": "Customer", "parent": ("in", customers)}, pluck="user")
    return sorted({u for u in users if frappe.db.get_value("User", u, "enabled")})


def notify(users, title, body, data=None):
    if not users or not _enabled():
        return
    tokens = frappe.get_all("Parent App Device", filters={"user": ("in", users), "enabled": 1}, pluck="push_token")
    if not tokens:
        return
    frappe.enqueue("baby_care.baby_care_management.utils.push.send", queue="short", enqueue_after_commit=True,
                   tokens=tokens, title=title, body=body, data=data or {})


def send(tokens, title, body, data=None):
    import requests

    messages = [{"to": t, "title": title, "body": body, "data": data or {}, "sound": "default"} for t in tokens]
    for i in range(0, len(messages), 100):
        batch = messages[i:i + 100]
        try:
            res = requests.post(EXPO_URL, json=batch, timeout=15, headers={"Accept": "application/json"})
            tickets = (res.json() or {}).get("data") or []
        except Exception as e:
            frappe.log_error(title="Baby Care: push send failed", message=str(e))
            continue
        for msg, ticket in zip(batch, tickets):
            if ticket.get("status") == "error":
                name = frappe.db.get_value("Parent App Device", {"push_token": msg["to"]}, "name")
                if name:
                    detail = (ticket.get("details") or {}).get("error")
                    values = {"last_error": f"{detail or ''} {ticket.get('message') or ''}".strip()[:500]}
                    if detail == "DeviceNotRegistered":
                        values["enabled"] = 0
                    frappe.db.set_value("Parent App Device", name, values, update_modified=False)
    frappe.db.commit()


def _child_name(child):
    return frappe.db.get_value("Child", child, "first_name") or child


# ── doc events ───────────────────────────────────────────────────────────────
def on_attendance_update(doc, method=None):
    before = doc.get_doc_before_save()
    name = _child_name(doc.child)
    data = {"type": "attendance", "child": doc.child, "date": str(doc.attendance_date)}
    if doc.check_in_time and (not before or not before.check_in_time):
        notify(parent_users_of_child(doc.child), _("{0} has arrived").format(name),
               _("Checked in at {0}").format(_hhmm(doc.check_in_time)), data)
    if doc.check_out_time and (not before or not before.check_out_time):
        who = _(" by {0}").format(doc.pickup_person) if doc.pickup_person else ""
        notify(parent_users_of_child(doc.child), _("{0} has left").format(name),
               _("Picked up at {0}{1}").format(_hhmm(doc.check_out_time), who), data)
    stype = frappe.db.get_value("Attendance Status", doc.status, "status_type") if doc.status else None
    if stype in ("Absent", "Leave") and (not before or before.status != doc.status):
        notify(parent_users_of_child(doc.child), _("{0} marked {1}").format(name, _(doc.status)),
               doc.get("absence_reason") or _("Attendance for {0}").format(frappe.format(doc.attendance_date, "Date")), data)


def on_incident_insert(doc, method=None):
    notify(parent_users_of_child(doc.child), _("Health note for {0}").format(_child_name(doc.child)),
           f"{_(doc.severity or '')}: {(doc.description or '')[:140]}",
           {"type": "incident", "child": doc.child})


def on_invoice_submit(doc, method=None):
    if not doc.get("baby_care_subscription"):
        return
    notify(parent_users_of_customers([doc.customer]), _("New invoice"),
           _("{0} — due {1}").format(_money(flt(doc.grand_total), doc.currency), frappe.format(doc.due_date, "Date")),
           {"type": "invoice", "invoice": doc.name})


def on_payment_submit(doc, method=None):
    if doc.party_type != "Customer" or doc.payment_type != "Receive":
        return
    notify(parent_users_of_customers([doc.party]), _("Payment received"),
           _("Thank you — {0} received.").format(_money(flt(doc.paid_amount), doc.paid_from_account_currency)),
           {"type": "payment", "payment": doc.name})
