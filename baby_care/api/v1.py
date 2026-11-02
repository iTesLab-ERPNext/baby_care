"""
Baby Care — Parent API v1
=========================

URL:  /api/method/baby_care.api.v1.<endpoint>
Docs: /parent-api   (OpenAPI JSON: /api/method/baby_care.api.v1.openapi)

A *parent* is a Website User listed in the **Portal Users** table of one or
more Customers (or linked to them through a Contact). Every endpoint works
only on the children and accounts of those Customers; anything else is
reported as "not found" so records cannot be probed.
"""
import json

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import add_days, cint, flt, getdate, today

from baby_care.api import spec

MAX_LIMIT = 100
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


# ── helpers ──────────────────────────────────────────────────────────────────
def _require_login():
    if frappe.session.user == "Guest":
        frappe.throw(_("Please log in."), frappe.AuthenticationError)


def parent_customers(user=None):
    """Customers this user may act for (Portal Users table, then Contact links)."""
    user = user or frappe.session.user
    customers = set(frappe.get_all("Portal User", filters={"user": user, "parenttype": "Customer"}, pluck="parent"))
    contacts = frappe.get_all("Contact", filters={"user": user}, pluck="name")
    if contacts:
        customers.update(frappe.get_all(
            "Dynamic Link",
            filters={"parenttype": "Contact", "parent": ("in", contacts), "link_doctype": "Customer"},
            pluck="link_name",
        ))
    return sorted(c for c in customers if frappe.db.exists("Customer", c))


def _customers():
    _require_login()
    customers = parent_customers()
    if not customers:
        frappe.throw(_("This account is not linked to a parent profile."), frappe.PermissionError)
    return customers


def _child_links(customers):
    return frappe.get_all(
        "Child Parent Link",
        filters={"parenttype": "Child", "parent_customer": ("in", customers)},
        fields=["parent as child", "relationship", "is_primary", "can_pickup", "parent_customer"],
    )


def _my_children(customers=None):
    customers = customers or _customers()
    return sorted({row.child for row in _child_links(customers)})


def _own_child(child):
    if not child:
        frappe.throw(_("Parameter 'child' is required."), frappe.ValidationError)
    if child not in _my_children():
        frappe.throw(_("Child {0} not found.").format(child), frappe.DoesNotExistError)
    return child


def _paging(limit=None, start=None):
    limit = cint(limit) or 20
    return max(1, min(limit, MAX_LIMIT)), max(0, cint(start))


def _date(value, default):
    if not value:
        return getdate(default)
    try:
        return getdate(value)
    except Exception:
        frappe.throw(_("Invalid date: {0}. Use YYYY-MM-DD.").format(value), frappe.ValidationError)


def _teacher_name(teacher):
    return frappe.db.get_value("Teacher Profile", teacher, "full_name") if teacher else None


def _status_types():
    return dict(frappe.get_all("Attendance Status", fields=["name", "status_type"], as_list=True))


def _attendance_summary(rows):
    types = _status_types()
    present = sum(1 for r in rows if types.get(r.status) in ("Present", "Late"))
    late = sum(1 for r in rows if types.get(r.status) == "Late")
    absent = sum(1 for r in rows if types.get(r.status) in ("Absent", "Leave"))
    counted = present + absent
    return {"present": present, "absent": absent, "late": late, "rate": round(present * 100.0 / counted, 1) if counted else None}


# ── authentication ───────────────────────────────────────────────────────────
@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=5 * 60)
def login(usr=None, pwd=None):
    if not usr or not pwd:
        frappe.throw(_("Both 'usr' and 'pwd' are required."), frappe.ValidationError)
    login_manager = getattr(frappe.local, "login_manager", None)
    if login_manager is None:  # outside a web request (tests, scripts)
        from frappe.auth import LoginManager

        login_manager = frappe.local.login_manager = LoginManager()
    login_manager.authenticate(user=usr, pwd=pwd)
    customers = parent_customers(login_manager.user)
    if not customers:
        frappe.throw(_("This account is not linked to a parent profile."), frappe.PermissionError)
    login_manager.post_login()
    frappe.local.response.pop("home_page", None)
    frappe.local.response.pop("full_name", None)
    from frappe.sessions import get_csrf_token

    return {
        "user": frappe.session.user,
        "full_name": frappe.utils.get_fullname(frappe.session.user),
        "sid": frappe.session.sid,
        "csrf_token": get_csrf_token(),
        "parents": _parents_info(customers),
        "children": _children_brief(customers),
    }


@frappe.whitelist(methods=["POST"])
def logout():
    _require_login()
    frappe.local.login_manager.logout()
    return {"ok": True}


# ── profile & children ───────────────────────────────────────────────────────
def _parents_info(customers):
    return frappe.get_all(
        "Customer",
        filters={"name": ("in", customers)},
        fields=["name as customer", "customer_name", "mobile_no", "email_id"],
        order_by="customer_name asc",
    )


def _children_brief(customers):
    names = _my_children(customers)
    if not names:
        return []
    return frappe.get_all("Child", filters={"name": ("in", names)}, fields=["name as child", "full_name"], order_by="full_name asc")


@frappe.whitelist(methods=["GET"])
def me():
    customers = _customers()
    from frappe.sessions import get_csrf_token

    return {
        "user": frappe.session.user,
        "full_name": frappe.utils.get_fullname(frappe.session.user),
        "csrf_token": get_csrf_token() if frappe.session.sid and frappe.session.sid != "Guest" else None,
        "parents": _parents_info(customers),
        "children": _children_brief(customers),
    }


@frappe.whitelist(methods=["GET"])
def children():
    customers = _customers()
    links = {}
    for row in _child_links(customers):
        links.setdefault(row.child, row)
    if not links:
        return []
    rows = frappe.get_all(
        "Child",
        filters={"name": ("in", list(links))},
        fields=["name as child", "full_name", "first_name", "last_name", "date_of_birth", "age_display as age", "gender", "photo",
                "enrollment_status", "registration_date", "nursery_class", "age_group", "assigned_teacher",
                "subscription_status", "has_allergies"],
        order_by="full_name asc",
    )
    for r in rows:
        r.teacher = _teacher_name(r.pop("assigned_teacher"))
        r.relationship = links[r.child].relationship
        r.is_primary_parent = links[r.child].is_primary
    return rows


@frappe.whitelist(methods=["GET"])
def child(child=None):
    child = _own_child(child)
    doc = frappe.get_doc("Child", child)
    teachers = [t for t in [_teacher_name(doc.assigned_teacher)] if t]
    if doc.nursery_class:
        for t in frappe.get_all("Nursery Class Teacher", filters={"parent": doc.nursery_class, "parenttype": "Nursery Class"}, pluck="teacher"):
            name = _teacher_name(t)
            if name and name not in teachers:
                teachers.append(name)
    med = frappe.db.get_value("Medical Record", {"child": child}, "name")
    allergies = frappe.get_all("Child Allergy", filters={"parent": med, "parenttype": "Medical Record"},
                               fields=["allergen", "severity", "reaction"]) if med else []
    vaccinations = frappe.get_all("Child Vaccination", filters={"parent": med, "parenttype": "Medical Record"},
                                  fields=["vaccine_name", "dose", "date_given", "next_due"], order_by="date_given asc") if med else []
    sub = _subscription_brief(doc.active_subscription)
    return {
        "child": doc.name,
        "full_name": doc.full_name,
        "first_name": doc.first_name,
        "last_name": doc.last_name,
        "date_of_birth": doc.date_of_birth,
        "age": doc.age_display,
        "gender": doc.gender,
        "photo": doc.photo,
        "enrollment_status": doc.enrollment_status,
        "registration_date": doc.registration_date,
        "nursery_class": doc.nursery_class,
        "age_group": doc.age_group,
        "teachers": teachers,
        "special_instructions": doc.special_instructions,
        "parents": [{"customer": p.parent_customer, "relationship": p.relationship, "is_primary": p.is_primary, "can_pickup": p.can_pickup} for p in doc.parents],
        "emergency_contacts": [{"full_name": c.full_name, "relationship": c.relationship, "phone": c.phone, "phone_alt": c.phone_alt} for c in doc.emergency_contacts],
        "authorized_pickups": [{"full_name": c.full_name, "relationship": c.relationship, "phone": c.phone} for c in doc.authorized_pickups],
        "allergies": allergies,
        "vaccinations": vaccinations,
        "subscription": sub,
    }


def _subscription_brief(name):
    if not name:
        return None
    s = frappe.db.get_value("Child Subscription", name,
                            ["name", "subscription_plan as plan", "status", "start_date", "end_date", "next_billing_date", "final_amount as amount_per_period", "currency"],
                            as_dict=True)
    return s


# ── follow-up ────────────────────────────────────────────────────────────────
@frappe.whitelist(methods=["GET"])
def child_attendance(child=None, from_date=None, to_date=None, limit=None, start=None):
    child = _own_child(child)
    to_d = _date(to_date, today())
    from_d = _date(from_date, add_days(to_d, -30))
    if from_d > to_d:
        frappe.throw(_("from_date must be before to_date."), frappe.ValidationError)
    limit, start = _paging(limit, start)
    filters = {"child": child, "attendance_date": ("between", [from_d, to_d])}
    every = frappe.get_all("Child Attendance", filters=filters, fields=["status"])
    rows = frappe.get_all(
        "Child Attendance",
        filters=filters,
        fields=["attendance_date as date", "status", "check_in_time", "check_out_time", "pickup_person as picked_up_by", "absence_reason", "notes"],
        order_by="attendance_date desc",
        limit_start=start,
        limit_page_length=limit,
    )
    return {"from_date": from_d, "to_date": to_d, "summary": _attendance_summary(every), "records": rows}


def _menu_for(child, day_date):
    day = DAYS[day_date.weekday()]
    plan, notes = None, None
    for p in frappe.get_all("Child Meal Plan", filters={"child": child, "is_active": 1},
                            fields=["meal_plan", "dietary_notes", "start_date", "end_date"], order_by="modified desc"):
        if (p.start_date and getdate(p.start_date) > day_date) or (p.end_date and getdate(p.end_date) < day_date):
            continue
        plan, notes = p.meal_plan, p.dietary_notes
        break
    if not plan:
        plan = frappe.db.get_value("Meal Plan", {"scope": "Global", "is_active": 1}, "name")
    items = []
    if plan:
        order = dict(frappe.get_all("Meal Category", fields=["name", "sort_order"], as_list=True))
        items = frappe.get_all("Meal Plan Item", filters={"parent": plan, "parenttype": "Meal Plan", "day_of_week": day},
                               fields=["meal_category", "menu_item", "allergens", "notes"])
        items.sort(key=lambda i: order.get(i.meal_category, 99))
    return {"date": day_date, "day": day, "meal_plan": plan, "dietary_notes": notes, "items": items}


@frappe.whitelist(methods=["GET"])
def child_meals(child=None, date=None):
    child = _own_child(child)
    return _menu_for(child, _date(date, today()))


@frappe.whitelist(methods=["GET"])
def child_incidents(child=None, limit=None, start=None):
    child = _own_child(child)
    limit, start = _paging(limit, start)
    return frappe.get_all(
        "Health Incident",
        filters={"child": child},
        fields=["incident_datetime as datetime", "severity", "incident_type", "description", "action_taken",
                "notified_parent as parent_notified", "parent_notified_at", "follow_up_required", "follow_up_notes"],
        order_by="incident_datetime desc",
        limit_start=start,
        limit_page_length=limit,
    )


@frappe.whitelist(methods=["GET"])
def child_documents(child=None):
    child = _own_child(child)
    from baby_care.baby_care_management.doctype.child_document.child_document import get_missing_mandatory_documents

    docs = frappe.get_all("Child Document", filters={"child": child},
                          fields=["document_type", "status", "issue_date", "expiry_date"], order_by="document_type asc")
    return {"documents": docs, "missing": [d for c, d in get_missing_mandatory_documents(child) if c == child]}


@frappe.whitelist(methods=["GET"])
def child_tracking(child=None, date=None):
    child = _own_child(child)
    day = _date(date, today())
    att = frappe.db.get_value(
        "Child Attendance", {"child": child, "attendance_date": day},
        ["status", "check_in_time", "check_out_time", "pickup_person as picked_up_by", "absence_reason"], as_dict=True,
    )
    last30 = frappe.get_all("Child Attendance", filters={"child": child, "attendance_date": ("between", [add_days(day, -30), day])}, fields=["status"])
    incidents = frappe.get_all("Health Incident", filters={"child": child},
                               fields=["incident_datetime as datetime", "severity", "incident_type", "description", "action_taken"],
                               order_by="incident_datetime desc", limit_page_length=5)
    med = frappe.db.get_value("Medical Record", {"child": child}, "name")
    vacc = frappe.get_all("Child Vaccination", filters={"parent": med, "parenttype": "Medical Record", "next_due": (">=", day)},
                          fields=["vaccine_name", "next_due"], order_by="next_due asc", limit_page_length=3) if med else []
    docs = child_documents(child)
    alerts = [{"document_type": d.document_type, "status": d.status, "expiry_date": d.expiry_date}
              for d in docs["documents"] if d.status in ("Expired", "Missing")
              or (d.expiry_date and getdate(d.expiry_date) <= getdate(add_days(day, 30)))]
    alerts += [{"document_type": m, "status": "Missing", "expiry_date": None} for m in docs["missing"]]
    sub = _subscription_brief(frappe.db.get_value("Child", child, "active_subscription"))
    return {
        "child": child,
        "full_name": frappe.db.get_value("Child", child, "full_name"),
        "date": day,
        "attendance": att or {"status": None, "check_in_time": None, "check_out_time": None, "picked_up_by": None, "absence_reason": None},
        "meals": _menu_for(child, day)["items"],
        "recent_incidents": incidents,
        "attendance_30_days": _attendance_summary(last30),
        "upcoming_vaccinations": vacc,
        "document_alerts": alerts,
        "subscription": sub and {k: sub[k] for k in ("status", "plan", "end_date", "next_billing_date")},
    }


# ── billing ──────────────────────────────────────────────────────────────────
@frappe.whitelist(methods=["GET"])
def subscriptions(child=None):
    customers = _customers()
    filters = {"parent_customer": ("in", customers), "docstatus": 1}
    if child:
        filters["child"] = _own_child(child)
    rows = frappe.get_all(
        "Child Subscription",
        filters=filters,
        fields=["name", "child", "subscription_plan as plan", "status", "start_date", "end_date", "next_billing_date",
                "final_amount as amount_per_period", "discount_percent", "currency"],
        order_by="start_date desc",
    )
    names = dict(frappe.get_all("Child", filters={"name": ("in", [r.child for r in rows] or [""])}, fields=["name", "full_name"], as_list=True))
    for r in rows:
        r.child_name = names.get(r.child)
    return rows


_INVOICE_STATUS = {
    "all": {},
    "unpaid": {"outstanding_amount": (">", 0)},
    "overdue": {"outstanding_amount": (">", 0), "due_date": ("<", today())},
    "paid": {"outstanding_amount": ("<=", 0)},
}


@frappe.whitelist(methods=["GET"])
def invoices(status="all", child=None, limit=None, start=None):
    customers = _customers()
    status = (status or "all").lower()
    if status not in _INVOICE_STATUS:
        frappe.throw(_("status must be one of: {0}").format(", ".join(_INVOICE_STATUS)), frappe.ValidationError)
    limit, start = _paging(limit, start)
    filters = {"customer": ("in", customers), "docstatus": 1, **_INVOICE_STATUS[status]}
    if status == "overdue":
        filters["due_date"] = ("<", today())
    if child:
        filters["baby_care_child"] = _own_child(child)
    return frappe.get_all(
        "Sales Invoice",
        filters=filters,
        fields=["name", "posting_date as date", "due_date", "customer", "baby_care_child as child", "baby_care_billing_period as billing_period",
                "grand_total", "outstanding_amount", "status", "currency", "is_return"],
        order_by="posting_date desc, name desc",
        limit_start=start,
        limit_page_length=limit,
    )


@frappe.whitelist(methods=["GET"])
def invoice(name=None):
    customers = _customers()
    if not name:
        frappe.throw(_("Parameter 'name' is required."), frappe.ValidationError)
    si = frappe.db.get_value("Sales Invoice", name, ["name", "customer", "docstatus"], as_dict=True)
    if not si or si.customer not in customers or si.docstatus != 1:
        frappe.throw(_("Invoice {0} not found.").format(name), frappe.DoesNotExistError)
    doc = frappe.get_doc("Sales Invoice", name)
    payments = frappe.db.sql(
        """select pe.name as payment_entry, pe.posting_date as date, per.allocated_amount as amount, pe.mode_of_payment
           from `tabPayment Entry Reference` per join `tabPayment Entry` pe on pe.name = per.parent
           where per.reference_doctype = 'Sales Invoice' and per.reference_name = %s and pe.docstatus = 1
           order by pe.posting_date""",
        name, as_dict=True,
    )
    return {
        "name": doc.name,
        "date": doc.posting_date,
        "due_date": doc.due_date,
        "customer": doc.customer,
        "child": doc.get("baby_care_child"),
        "billing_period": doc.get("baby_care_billing_period"),
        "currency": doc.currency,
        "net_total": doc.net_total,
        "discount_amount": doc.discount_amount,
        "total_taxes": doc.total_taxes_and_charges,
        "grand_total": doc.grand_total,
        "outstanding_amount": doc.outstanding_amount,
        "status": doc.status,
        "items": [{"item": i.item_name, "description": i.description, "qty": i.qty, "rate": i.rate, "amount": i.amount} for i in doc.items],
        "taxes": [{"description": t.description, "rate": t.rate, "amount": t.tax_amount} for t in doc.taxes],
        "payments": payments,
    }


@frappe.whitelist(methods=["GET"])
def payments(limit=None, start=None):
    customers = _customers()
    limit, start = _paging(limit, start)
    rows = frappe.get_all(
        "Payment Entry",
        filters={"party_type": "Customer", "party": ("in", customers), "docstatus": 1, "payment_type": "Receive"},
        fields=["name", "posting_date as date", "paid_amount as amount", "mode_of_payment", "reference_no", "reference_date",
                "paid_from_account_currency as currency", "party as customer"],
        order_by="posting_date desc, name desc",
        limit_start=start,
        limit_page_length=limit,
    )
    for r in rows:
        r.invoices = frappe.get_all(
            "Payment Entry Reference",
            filters={"parent": r.name, "parenttype": "Payment Entry", "reference_doctype": "Sales Invoice"},
            fields=["reference_name as invoice", "allocated_amount"],
        )
    return rows


@frappe.whitelist(methods=["GET"])
def balance():
    customers = _customers()
    rows = frappe.get_all(
        "Sales Invoice",
        filters={"customer": ("in", customers), "docstatus": 1},
        fields=["grand_total", "outstanding_amount", "due_date", "currency", "baby_care_child as child"],
    )
    t = getdate(today())
    out = {
        "currency": rows[0].currency if rows else None,
        "invoiced": sum(flt(r.grand_total) for r in rows),
        "outstanding": sum(flt(r.outstanding_amount) for r in rows),
        "overdue": sum(flt(r.outstanding_amount) for r in rows if flt(r.outstanding_amount) > 0 and r.due_date and getdate(r.due_date) < t),
    }
    out["paid"] = out["invoiced"] - out["outstanding"]
    due = sorted(getdate(r.due_date) for r in rows if flt(r.outstanding_amount) > 0 and r.due_date and getdate(r.due_date) >= t)
    out["next_due_date"] = due[0] if due else None
    names = dict(frappe.get_all("Child", filters={"name": ("in", _my_children(customers) or [""])}, fields=["name", "full_name"], as_list=True))
    per = {}
    for r in rows:
        key = r.child or ""
        p = per.setdefault(key, {"child": r.child, "child_name": names.get(r.child), "invoiced": 0.0, "outstanding": 0.0})
        p["invoiced"] += flt(r.grand_total)
        p["outstanding"] += flt(r.outstanding_amount)
    out["by_child"] = list(per.values())
    return out


# ── documentation ────────────────────────────────────────────────────────────
@frappe.whitelist(allow_guest=True, methods=["GET"])
def openapi():
    """OpenAPI 3 description of this API (raw JSON, usable by Swagger UI / Postman)."""
    frappe.response["type"] = "download"
    frappe.response["filename"] = "baby_care_parent_api.json"
    frappe.response["content_type"] = "application/json"
    frappe.response["display_content_as"] = "inline"
    frappe.response["filecontent"] = json.dumps(spec.openapi(frappe.utils.get_url()), indent=2, default=str)
