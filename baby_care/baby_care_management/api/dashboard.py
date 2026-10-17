"""
Number-card data for the Baby Care workspace and dashboard.

Every figure is computed from database records with the *current user's*
permissions (frappe.get_list / count via get_list), so a teacher sees counts
for their own children and finance cards show 0 to users without finance
access instead of leaking totals.
"""
import frappe
from frappe.utils import add_days, flt, get_first_day, get_last_day, getdate, today


def _card(value, fieldtype="Int", route=None, route_options=None):
    out = {"value": value, "fieldtype": fieldtype}
    if route:
        out["route"] = route
    if route_options:
        out["route_options"] = route_options
    return out


def _count(doctype, filters):
    if not frappe.has_permission(doctype, "read"):
        return 0
    return len(frappe.get_list(doctype, filters=filters, pluck="name", limit_page_length=0))


def _sum(doctype, field, filters):
    if not frappe.has_permission(doctype, "read"):
        return 0
    rows = frappe.get_list(doctype, filters=filters, fields=[f"sum({field}) as total"], limit_page_length=0)
    return flt(rows[0].total) if rows else 0


def _quarter_start(d):
    d = getdate(d)
    return d.replace(month=3 * ((d.month - 1) // 3) + 1, day=1)


@frappe.whitelist()
def enrolled_children(filters=None):
    f = {"enrollment_status": "Active"}
    return _card(_count("Child", f), route=["List", "Child"], route_options=f)


@frappe.whitelist()
def active_parents(filters=None):
    if not frappe.has_permission("Child", "read"):
        return _card(0)
    children = frappe.get_list("Child", filters={"enrollment_status": "Active"}, pluck="name", limit_page_length=0)
    if not children:
        return _card(0)
    parents = frappe.get_all("Child Parent Link", filters={"parenttype": "Child", "parent": ("in", children)}, pluck="parent_customer", distinct=True)
    return _card(len(set(parents)), route=["List", "Customer"])


def _attendance_today(status_type):
    statuses = frappe.get_all("Attendance Status", filters={"status_type": ("in", status_type)}, pluck="name")
    if not statuses:
        return 0, {}
    f = {"attendance_date": today(), "status": ("in", statuses)}
    return _count("Child Attendance", f), f


@frappe.whitelist()
def present_today(filters=None):
    n, f = _attendance_today(["Present", "Late"])
    return _card(n, route=["List", "Child Attendance"], route_options={"attendance_date": today()})


@frappe.whitelist()
def absent_today(filters=None):
    n, f = _attendance_today(["Absent", "Leave"])
    return _card(n, route=["List", "Child Attendance"], route_options={"attendance_date": today()})


@frappe.whitelist()
def active_subscriptions(filters=None):
    f = {"docstatus": 1, "status": "Active"}
    return _card(_count("Child Subscription", f), route=["List", "Child Subscription"], route_options={"status": "Active"})


@frappe.whitelist()
def expiring_subscriptions(filters=None):
    days = frappe.db.get_single_value("Nursery Settings", "notify_subscription_expiry_days") or 14
    f = {"docstatus": 1, "status": "Active", "end_date": ("between", [today(), add_days(today(), days)])}
    return _card(_count("Child Subscription", f), route=["List", "Child Subscription"], route_options={"status": "Active"})


_NURSERY_SI = {"docstatus": 1, "baby_care_subscription": ("is", "set")}


@frappe.whitelist()
def monthly_revenue(filters=None):
    f = dict(_NURSERY_SI, posting_date=("between", [get_first_day(today()), get_last_day(today())]))
    return _card(_sum("Sales Invoice", "base_grand_total", f), "Currency", route=["query-report", "Revenue Report"])


@frappe.whitelist()
def quarterly_revenue(filters=None):
    start = _quarter_start(today())
    f = dict(_NURSERY_SI, posting_date=("between", [start, add_days(frappe.utils.add_months(start, 3), -1)]))
    return _card(_sum("Sales Invoice", "base_grand_total", f), "Currency", route=["query-report", "Revenue Report"])


@frappe.whitelist()
def outstanding_payments(filters=None):
    f = dict(_NURSERY_SI, outstanding_amount=(">", 0))
    return _card(_sum("Sales Invoice", "outstanding_amount", f), "Currency", route=["query-report", "Outstanding Payments"])


@frappe.whitelist()
def overdue_invoices(filters=None):
    f = dict(_NURSERY_SI, outstanding_amount=(">", 0), due_date=("<", today()))
    return _card(_count("Sales Invoice", f), route=["query-report", "Outstanding Payments"])


@frappe.whitelist()
def active_teachers(filters=None):
    f = {"employment_status": "Active"}
    return _card(_count("Teacher Profile", f), route=["List", "Teacher Profile"], route_options=f)


@frappe.whitelist()
def missing_documents(filters=None):
    if not frappe.has_permission("Child Document", "read"):
        return _card(0)
    from baby_care.baby_care_management.doctype.child_document.child_document import get_missing_mandatory_documents

    visible = set(frappe.get_list("Child", filters={"enrollment_status": "Active"}, pluck="name", limit_page_length=0))
    expired = _count("Child Document", {"status": ("in", ["Expired", "Missing"])})
    missing = len([1 for c, _ in get_missing_mandatory_documents() if c in visible])
    return _card(missing + expired, route=["query-report", "Medical and Document Alerts"])


@frappe.whitelist()
def upcoming_birthdays(filters=None):
    if not frappe.has_permission("Child", "read"):
        return _card(0)
    t = getdate(today())
    n = 0
    for dob in frappe.get_list("Child", filters={"enrollment_status": "Active", "date_of_birth": ("is", "set")}, pluck="date_of_birth", limit_page_length=0):
        dob = getdate(dob)
        try:
            b = dob.replace(year=t.year)
        except ValueError:
            b = dob.replace(year=t.year, day=28)
        if 0 <= (b - t).days <= 30:
            n += 1
    return _card(n, route=["query-report", "Enrolled Children Summary"])
