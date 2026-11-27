"""
Baby Care — Parent API v1
=========================

URL:  /api/method/baby_care.api.v1.<endpoint>
Docs: /parent-api   (OpenAPI JSON: /api/method/baby_care.api.v1.openapi)

A *parent* is a Frappe Website User linked to a **Parent Profile** (its
``user`` field, set from the profile's "Parent App" tab). Every endpoint works
only on the children, invoices and payments of that profile; anything else is
reported as "not found" so records cannot be probed.
"""
import json

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import add_days, cint, flt, fmt_money, formatdate, getdate, today

from baby_care.api import spec


def _hhmm(t):
    """'8:00:00' / timedelta -> '08:00'."""
    parts = str(t or "").split(":")
    return f"{int(parts[0]):02d}:{parts[1][:2]}" if len(parts) >= 2 and parts[0].strip().isdigit() else ""


def _money(amount, currency=None):
    """'TND 999.000' — currency code, not the symbol: some symbols are right-to-left
    (e.g. د.ت) and scramble a left-to-right sentence on the phone."""
    return f"{currency or ''} {fmt_money(flt(amount))}".strip()

MAX_LIMIT = 100
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


# ── helpers ──────────────────────────────────────────────────────────────────
APP_LANGUAGES = ("fr", "en", "ar")


def _apply_app_language():
    """Answer in the language the mobile app is using (header X-BabyCare-Lang)."""
    try:
        lang = (frappe.get_request_header("X-BabyCare-Lang") or "").strip().lower()[:2]
    except Exception:  # not in a request (tests, console)
        return
    if lang in APP_LANGUAGES and frappe.local.lang != lang:
        frappe.local.lang = lang


def _require_login():
    _apply_app_language()
    if frappe.session.user == "Guest":
        frappe.throw(_("Please log in."), frappe.AuthenticationError)


def parent_profiles(user=None):
    """Parent Profiles this user may act for (active profiles with app access)."""
    user = user or frappe.session.user
    if not user or user == "Guest":
        return []
    return sorted(frappe.get_all("Parent Profile", filters={"user": user, "app_access": 1, "is_active": 1}, pluck="name"))


def _parents():
    _require_login()
    parents = parent_profiles()
    if not parents:
        frappe.throw(_("This account is not linked to a parent profile."), frappe.PermissionError)
    return parents


def _child_links(parents):
    return frappe.get_all(
        "Child Parent Link",
        filters={"parenttype": "Child", "parent_profile": ("in", parents)},
        fields=["parent as child", "relationship", "is_primary", "can_pickup", "parent_profile"],
    )


def _my_children(parents=None):
    parents = parents or _parents()
    return sorted({row.child for row in _child_links(parents)})


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
    parents = parent_profiles(login_manager.user)
    if not parents:
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
        "parents": _parents_info(parents),
        "children": _children_brief(parents),
    }


@frappe.whitelist(methods=["POST"])
def logout():
    _require_login()
    frappe.local.login_manager.logout()
    return {"ok": True}


# ── profile & children ───────────────────────────────────────────────────────
def _parents_info(parents):
    return frappe.get_all(
        "Parent Profile",
        filters={"name": ("in", parents)},
        fields=["name as parent", "full_name", "relationship", "mobile_no", "email"],
        order_by="full_name asc",
    )


def _children_brief(parents):
    names = _my_children(parents)
    if not names:
        return []
    return frappe.get_all("Child", filters={"name": ("in", names)}, fields=["name as child", "full_name"], order_by="full_name asc")


@frappe.whitelist(methods=["GET"])
def me():
    parents = _parents()
    from frappe.sessions import get_csrf_token

    return {
        "user": frappe.session.user,
        "full_name": frappe.utils.get_fullname(frappe.session.user),
        "csrf_token": get_csrf_token() if frappe.session.sid and frappe.session.sid != "Guest" else None,
        "parents": _parents_info(parents),
        "children": _children_brief(parents),
    }


@frappe.whitelist(methods=["GET"])
def children():
    parents = _parents()
    links = {}
    for row in _child_links(parents):
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
        "parents": [{"parent": p.parent_profile, "full_name": p.parent_name, "relationship": p.relationship, "is_primary": p.is_primary, "can_pickup": p.can_pickup} for p in doc.parents],
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
    parents = _parents()
    filters = {"parent_profile": ("in", parents), "docstatus": 1}
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


_INV_FIELDS = ["name", "posting_date as date", "due_date", "parent_profile as parent", "child", "billing_period",
               "grand_total", "paid_amount", "outstanding_amount", "status", "currency"]


@frappe.whitelist(methods=["GET"])
def invoices(status="all", child=None, limit=None, start=None):
    parents = _parents()
    status = (status or "all").lower()
    if status not in _INVOICE_STATUS:
        frappe.throw(_("status must be one of: {0}").format(", ".join(_INVOICE_STATUS)), frappe.ValidationError)
    limit, start = _paging(limit, start)
    filters = {"parent_profile": ("in", parents), "docstatus": 1, **_INVOICE_STATUS[status]}
    if child:
        filters["child"] = _own_child(child)
    return frappe.get_all("Nursery Invoice", filters=filters, fields=_INV_FIELDS,
                          order_by="posting_date desc, name desc", limit_start=start, limit_page_length=limit)


@frappe.whitelist(methods=["GET"])
def invoice(name=None):
    parents = _parents()
    if not name:
        frappe.throw(_("Parameter 'name' is required."), frappe.ValidationError)
    inv = frappe.db.get_value("Nursery Invoice", name, ["name", "parent_profile", "docstatus"], as_dict=True)
    if not inv or inv.parent_profile not in parents or inv.docstatus != 1:
        frappe.throw(_("Invoice {0} not found.").format(name), frappe.DoesNotExistError)
    doc = frappe.get_doc("Nursery Invoice", name)
    payments = frappe.db.sql(
        """select p.name as payment, p.payment_date as date, a.allocated_amount as amount, p.mode_of_payment
           from `tabNursery Payment Allocation` a join `tabNursery Payment` p on p.name = a.parent
           where a.parenttype = 'Nursery Payment' and a.invoice = %s and p.docstatus = 1
           order by p.payment_date""",
        name, as_dict=True,
    )
    taxes = [{"description": _("Tax {0}%").format(flt(doc.tax_rate)), "rate": flt(doc.tax_rate), "amount": doc.tax_amount}] if flt(doc.tax_amount) else []
    return {
        "name": doc.name,
        "date": doc.posting_date,
        "due_date": doc.due_date,
        "parent": doc.parent_profile,
        "child": doc.child,
        "billing_period": doc.billing_period,
        "currency": doc.currency,
        "net_total": doc.total,
        "discount_amount": doc.discount_amount,
        "total_taxes": doc.tax_amount,
        "grand_total": doc.grand_total,
        "paid_amount": doc.paid_amount,
        "outstanding_amount": doc.outstanding_amount,
        "status": doc.status,
        "items": [{"item": i.service, "description": i.description, "qty": i.qty, "rate": i.rate, "amount": i.amount} for i in doc.items],
        "taxes": taxes,
        "payments": payments,
        "payment_instructions": frappe.db.get_single_value("Nursery Settings", "invoice_footer"),
    }


@frappe.whitelist(methods=["GET"])
def payments(limit=None, start=None):
    parents = _parents()
    limit, start = _paging(limit, start)
    rows = frappe.get_all(
        "Nursery Payment",
        filters={"parent_profile": ("in", parents), "docstatus": 1},
        fields=["name", "payment_date as date", "amount", "mode_of_payment", "reference_no", "reference_date", "currency",
                "parent_profile as parent", "unallocated_amount"],
        order_by="payment_date desc, name desc",
        limit_start=start,
        limit_page_length=limit,
    )
    for r in rows:
        r.invoices = frappe.get_all("Nursery Payment Allocation", filters={"parent": r.name, "parenttype": "Nursery Payment"},
                                    fields=["invoice", "allocated_amount"], order_by="idx")
    return rows


@frappe.whitelist(methods=["GET"])
def balance():
    parents = _parents()
    rows = frappe.get_all("Nursery Invoice", filters={"parent_profile": ("in", parents), "docstatus": 1},
                          fields=["grand_total", "outstanding_amount", "due_date", "currency", "child"])
    t = getdate(today())
    from baby_care.baby_care_management.utils.billing import default_currency, parent_credit

    out = {
        "currency": rows[0].currency if rows else default_currency(),
        "invoiced": sum(flt(r.grand_total) for r in rows),
        "outstanding": sum(flt(r.outstanding_amount) for r in rows),
        "overdue": sum(flt(r.outstanding_amount) for r in rows if flt(r.outstanding_amount) > 0 and r.due_date and getdate(r.due_date) < t),
        "credit": sum(parent_credit(p) for p in parents),
    }
    out["paid"] = out["invoiced"] - out["outstanding"]
    due = sorted(getdate(r.due_date) for r in rows if flt(r.outstanding_amount) > 0 and r.due_date and getdate(r.due_date) >= t)
    out["next_due_date"] = due[0] if due else None
    names = dict(frappe.get_all("Child", filters={"name": ("in", _my_children(parents) or [""])}, fields=["name", "full_name"], as_list=True))
    per = {}
    for r in rows:
        key = r.child or ""
        p = per.setdefault(key, {"child": r.child, "child_name": names.get(r.child), "invoiced": 0.0, "outstanding": 0.0})
        p["invoiced"] += flt(r.grand_total)
        p["outstanding"] += flt(r.outstanding_amount)
    out["by_child"] = list(per.values())
    return out


# ── mobile app ───────────────────────────────────────────────────────────────
def _login_manager():
    lm = getattr(frappe.local, "login_manager", None)
    if lm is None:
        from frappe.auth import LoginManager

        lm = frappe.local.login_manager = LoginManager()
    return lm


def _api_token(user, rotate=False):
    """`api_key:api_secret` for token auth (`Authorization: token …`)."""
    from frappe.utils.password import get_decrypted_password, set_encrypted_password

    key = frappe.db.get_value("User", user, "api_key")
    secret = None if rotate or not key else get_decrypted_password("User", user, "api_secret", raise_exception=False)
    if not key:
        key = frappe.generate_hash(length=15)
        frappe.db.set_value("User", user, "api_key", key, update_modified=False)
    if not secret:
        secret = frappe.generate_hash(length=15)
        set_encrypted_password("User", user, secret, "api_secret")
    return f"{key}:{secret}"


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=5 * 60)
def app_login(usr=None, pwd=None, device_name=None):
    """Mobile login: returns a long-lived token instead of a browser session."""
    _apply_app_language()
    if not usr or not pwd:
        frappe.throw(_("Both 'usr' and 'pwd' are required."), frappe.ValidationError)
    lm = _login_manager()
    lm.authenticate(user=(usr or "").strip(), pwd=pwd)
    user = lm.user
    parents = parent_profiles(user)
    if not parents or "Nursery Parent" not in frappe.get_roles(user):
        frappe.throw(_("This account is not linked to a parent profile."), frappe.PermissionError)
    token = _api_token(user)
    frappe.db.set_value("User", user, "last_login", frappe.utils.now(), update_modified=False)
    frappe.db.commit()
    return {
        "token": token,
        "user": user,
        "full_name": frappe.utils.get_fullname(user),
        "parents": _parents_info(parents),
        "children": _children_brief(parents),
        "app": app_info(),
    }


@frappe.whitelist(methods=["POST"])
def app_logout(all_devices=0, push_token=None):
    """Forget this phone's push token; with all_devices=1 also invalidate every app token."""
    _parents()
    if push_token:
        frappe.db.delete("Parent App Device", {"user": frappe.session.user, "push_token": push_token})
    if cint(all_devices):
        _api_token(frappe.session.user, rotate=True)
        frappe.db.delete("Parent App Device", {"user": frappe.session.user})
    return {"ok": True}


@frappe.whitelist(methods=["POST"])
def change_password(old_password=None, new_password=None):
    """Change the parent's password. Returns a new token: other phones are signed out."""
    _parents()
    if not old_password or not new_password:
        frappe.throw(_("Both 'old_password' and 'new_password' are required."), frappe.ValidationError)
    from frappe.utils.password import check_password, update_password

    user = frappe.session.user
    try:
        check_password(user, old_password)
    except frappe.AuthenticationError:
        frappe.throw(_("The current password is not correct."), frappe.ValidationError)
    if new_password == old_password:
        frappe.throw(_("Choose a password different from the current one."), frappe.ValidationError)
    from baby_care.baby_care_management.utils.parent_access import check_strength

    check_strength(new_password, user)
    update_password(user, new_password)
    return {"ok": True, "token": _api_token(user, rotate=True)}


@frappe.whitelist(allow_guest=True, methods=["GET"])
def app_info():
    """Public facts the app shows before login (name, logo, currency)."""
    _apply_app_language()
    s = frappe.get_cached_doc("Nursery Settings")
    return {
        "name": s.get("parent_app_name") or s.get("facility_name") or _("Baby Care"),
        "facility_type": s.get("facility_type"),
        "logo": "/assets/baby_care/images/baby_care_logo.svg",
        "currency": s.get("default_currency"),
        "api_version": spec.VERSION,
        "push_enabled": bool(cint(s.get("enable_push_notifications"))),
    }


@frappe.whitelist(methods=["POST"])
def register_device(push_token=None, platform=None, device_name=None, app_version=None):
    """Store this phone's Expo push token so the nursery can notify the parent."""
    _parents()
    token = (push_token or "").strip()
    if not token.startswith(("ExponentPushToken[", "ExpoPushToken[")):
        frappe.throw(_("Invalid Expo push token."), frappe.ValidationError)
    values = {"user": frappe.session.user, "platform": (platform or "")[:20] if platform in ("ios", "android", "web") else "",
              "device_name": (device_name or "")[:140], "app_version": (app_version or "")[:40], "enabled": 1,
              "last_seen": frappe.utils.now(), "last_error": None}
    name = frappe.db.get_value("Parent App Device", {"push_token": token}, "name")
    if name:
        frappe.db.set_value("Parent App Device", name, values)
    else:
        frappe.get_doc(dict(values, doctype="Parent App Device", push_token=token)).insert(ignore_permissions=True)
    return {"ok": True}


@frappe.whitelist(methods=["GET"])
def notifications(days=30, limit=None, start=None):
    """Activity feed for the parent: arrivals and departures, health notes,
    invoices, payments, document and subscription reminders — newest first."""
    parents = _parents()
    limit, start = _paging(limit or 50, start)
    days = max(1, min(cint(days) or 30, 180))
    since = add_days(today(), -days)
    kids = _my_children(parents)
    names = dict(frappe.get_all("Child", filters={"name": ("in", kids or [""])}, fields=["name", "first_name"], as_list=True))
    feed = []
    types = _status_types()

    def add(kind, key, when, title, body, child=None, ref=None):
        feed.append({"id": f"{kind}:{key}", "type": kind, "datetime": str(when), "title": title, "body": body,
                     "child": child, "child_name": names.get(child), "ref": ref})

    if kids:
        for a in frappe.get_all("Child Attendance", filters={"child": ("in", kids), "attendance_date": (">=", since)},
                                fields=["name", "child", "attendance_date", "status", "check_in_time", "check_out_time", "pickup_person", "absence_reason"]):
            n = names.get(a.child)
            if a.check_in_time:
                add("check_in", a.name, f"{a.attendance_date} {a.check_in_time}", _("{0} has arrived").format(n),
                    _("Checked in at {0}").format(_hhmm(a.check_in_time)), a.child, a.name)
            if a.check_out_time:
                by = _(" by {0}").format(a.pickup_person) if a.pickup_person else ""
                add("check_out", a.name, f"{a.attendance_date} {a.check_out_time}", _("{0} has left").format(n),
                    _("Picked up at {0}{1}").format(_hhmm(a.check_out_time), by), a.child, a.name)
            if not a.check_in_time and types.get(a.status) in ("Absent", "Leave"):
                add("absence", a.name, f"{a.attendance_date} 08:00:00", _("{0} marked {1}").format(n, _(a.status)),
                    a.absence_reason or "", a.child, a.name)
        for i in frappe.get_all("Health Incident", filters={"child": ("in", kids), "incident_datetime": (">=", since)},
                                fields=["name", "child", "incident_datetime", "severity", "description", "action_taken"]):
            add("incident", i.name, i.incident_datetime, _("Health note for {0}").format(names.get(i.child)),
                f"{_(i.severity or '')}: {i.description or ''}" + (f" — {i.action_taken}" if i.action_taken else ""), i.child, i.name)
        for d in frappe.get_all("Child Document", filters={"child": ("in", kids), "status": ("in", ["Expired", "Missing"])},
                                fields=["name", "child", "document_type", "status", "modified"]):
            add("document", d.name, d.modified, _("Document needed: {0}").format(_(d.document_type)),
                _("{0} — {1}").format(names.get(d.child), _(d.status)), d.child, d.name)
    for si in frappe.get_all("Nursery Invoice", filters={"parent_profile": ("in", parents), "docstatus": 1, "posting_date": (">=", since)},
                             fields=["name", "posting_date", "creation", "grand_total", "due_date", "currency", "child"]):
        add("invoice", si.name, si.creation, _("New invoice {0}").format(si.name),
            _("{0} — due {1}").format(_money(si.grand_total, si.currency), formatdate(si.due_date)), si.child, si.name)
    for pe in frappe.get_all("Nursery Payment", filters={"parent_profile": ("in", parents), "docstatus": 1, "payment_date": (">=", since)},
                             fields=["name", "creation", "amount", "currency"]):
        add("payment", pe.name, pe.creation, _("Payment received"),
            _("{0} — thank you").format(_money(pe.amount, pe.currency)), None, pe.name)
    for si in frappe.get_all("Nursery Invoice", filters={"parent_profile": ("in", parents), "docstatus": 1, "outstanding_amount": (">", 0),
                                                         "due_date": ("<", today())},
                             fields=["name", "due_date", "outstanding_amount", "currency", "child"]):
        add("overdue", si.name, f"{si.due_date} 09:00:00", _("Invoice {0} is overdue").format(si.name),
            _("{0} still to pay").format(_money(si.outstanding_amount, si.currency)), si.child, si.name)
    for sub in frappe.get_all("Child Subscription", filters={"parent_profile": ("in", parents), "docstatus": 1, "status": "Active",
                                                             "end_date": ("between", [today(), add_days(today(), 30)])},
                              fields=["name", "child", "end_date"]):
        add("subscription", sub.name, f"{add_days(sub.end_date, -30)} 09:00:00", _("Subscription ends soon"),
            _("{0}'s subscription ends on {1}").format(names.get(sub.child), sub.end_date), sub.child, sub.name)
    for n in frappe.get_all("Notification Log", filters={"for_user": frappe.session.user, "creation": (">=", since)},
                            fields=["name", "creation", "subject", "email_content"]):
        add("message", n.name, n.creation, frappe.utils.strip_html(n.subject or ""), frappe.utils.strip_html(n.email_content or "")[:300])

    feed.sort(key=lambda x: x["datetime"], reverse=True)
    return feed[start:start + limit]


# ── documentation ────────────────────────────────────────────────────────────
@frappe.whitelist(allow_guest=True, methods=["GET"])
def openapi():
    """OpenAPI 3 description of this API (raw JSON, usable by Swagger UI / Postman)."""
    frappe.response["type"] = "download"
    frappe.response["filename"] = "baby_care_parent_api.json"
    frappe.response["content_type"] = "application/json"
    frappe.response["display_content_as"] = "inline"
    frappe.response["filecontent"] = json.dumps(spec.openapi(frappe.utils.get_url()), indent=2, default=str)
