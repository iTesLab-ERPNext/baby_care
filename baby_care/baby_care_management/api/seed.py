"""
Seed / test data management (used by the "Baby Care Data Management" page).

* install_master_data  – configuration defaults, created on install/migrate.
* install_seed_data    – starter catalogue: services, plans, a meal plan, a route.
* install_test_data    – demo parents, children, teachers, attendance,
                         subscriptions … every record created is tracked.
* clear_test_data      – removes exactly the tracked demo records.
"""
import json

import frappe
from frappe import _
from frappe.utils import add_days, add_months, add_years, flt, getdate, today

ADMINS = ("System Manager", "Nursery Administrator")
REGISTRY_KEY = "baby_care_test_data"


def _only_admins():
    frappe.only_for(ADMINS)


def _insert(doc_dict, track=None):
    doc = frappe.get_doc(doc_dict)
    doc.insert(ignore_permissions=True)
    if track is not None:
        track.append([doc.doctype, doc.name])
    return doc


def _ensure(doctype, name, values):
    if frappe.db.exists(doctype, name):
        return False
    _insert(dict({"doctype": doctype}, **values))
    return True


# ── master data (automatic) ──────────────────────────────────────────────────
def install_master_data():
    settings = frappe.get_single("Nursery Settings")
    if not settings.facility_name:
        settings.update({
            "facility_name": "My Nursery",
            "facility_type": "Nursery",
            "invoice_generation_day": 0,
            "invoice_due_days": 15,
            "allow_partial_payment": 1,
            "auto_generate_invoices": 1,
            "auto_submit_invoices": 1,
            "enforce_class_capacity": 1,
            "enforce_pickup_verification": 1,
            "enable_transportation": 1,
            "notify_subscription_expiry_days": 14,
            "notify_document_expiry_days": 30,
            "notify_overdue_after_days": 7,
        })
    if not settings.default_currency:
        settings.default_currency = frappe.db.get_default("currency") or ("TND" if frappe.db.exists("Currency", "TND") else None)
    settings.flags.ignore_permissions = True
    settings.flags.ignore_mandatory = True
    settings.save()

    for name, lo, hi in (("Infants", 0, 12), ("Toddlers", 12, 36), ("Preschool", 36, 60), ("Kindergarten", 60, 84)):
        _ensure("Age Group", name, {"group_name": name, "min_age_months": lo, "max_age_months": hi, "is_active": 1})
    for i, cat in enumerate(("Breakfast", "Morning Snack", "Lunch", "Afternoon Snack", "Dinner")):
        _ensure("Meal Category", cat, {"category_name": cat, "sort_order": i, "is_active": 1})
    for name, stype, color in (("Present", "Present", "Green"), ("Absent", "Absent", "Red"), ("Late", "Late", "Orange"),
                               ("Leave", "Leave", "Blue"), ("Holiday", "Holiday", "Grey")):
        _ensure("Attendance Status", name, {"status_name": name, "status_type": stype, "color": color, "is_active": 1})
    for cat in ("Meals", "Transportation", "Education", "Extracurricular", "Extended Hours", "Hygiene", "Other"):
        _ensure("Service Category", cat, {"category_name": cat, "is_active": 1})
    for name, applies, mandatory, expiry in (
        ("Birth Certificate", "Child", 1, 0),
        ("Vaccination Card", "Child", 1, 1),
        ("Medical Certificate", "Child", 0, 1),
        ("Enrollment Form", "Child", 1, 0),
        ("Insurance Certificate", "Child", 0, 1),
        ("Pickup Authorization", "Child", 0, 0),
        ("Parent Identification", "Parent", 1, 1),
    ):
        _ensure("Document Type Config", name, {"document_name": name, "applies_to": applies, "is_mandatory": mandatory, "has_expiry": expiry, "is_active": 1})


# ── starter catalogue (button) ───────────────────────────────────────────────
@frappe.whitelist()
def install_seed_data():
    _only_admins()
    install_master_data()
    if not frappe.db.get_single_value("Nursery Settings", "multi_child_discount_percent"):
        frappe.db.set_single_value("Nursery Settings", "multi_child_discount_percent", 10)
    currency = frappe.db.get_single_value("Nursery Settings", "default_currency")
    created = 0
    services = (
        ("Lunch Service", "Meals", "Monthly", 60, "Monthly", 1),
        ("Morning Transport", "Transportation", "Monthly", 40, "Monthly", 1),
        ("Extended Hours (until 18:00)", "Extended Hours", "Monthly", 50, "Monthly", 1),
        ("Music Workshop", "Extracurricular", "Monthly", 25, "Monthly", 1),
        ("Hygiene Kit", "Hygiene", "Included in Subscription", 0, "Included", 0),
    )
    for name, cat, method, price, freq, optional in services:
        created += _ensure("Nursery Service", name, {
            "service_name": name, "category": cat, "pricing_method": method, "price": price, "billing_frequency": freq,
            "is_active": 1, "is_optional": optional, "availability": "All", "scope": "Global",
        })
    for name, freq, months, price in (("Monthly Full Day", "Monthly", 12, 350), ("Quarterly Full Day", "Quarterly", 12, 990), ("Annual Full Day", "Annual", 12, 3700)):
        created += _ensure("Subscription Plan", name, {
            "plan_name": name, "billing_frequency": freq, "duration_months": months, "base_price": price, "currency": currency,
            "renewal_type": "Manual", "is_active": 1,
            "services": [{"service": "Hygiene Kit", "is_included": 1}],
        })
    if not frappe.db.exists("Meal Plan", "Standard Week"):
        items = []
        menu = {"Monday": ("Porridge", "Chicken & rice", "gluten"), "Tuesday": ("Yogurt & fruit", "Fish & vegetables", "milk, fish"),
                "Wednesday": ("Bread & cheese", "Pasta bolognese", "gluten, milk"), "Thursday": ("Fruit salad", "Lentil soup", ""),
                "Friday": ("Pancakes", "Couscous & vegetables", "gluten, egg")}
        for day, (breakfast, lunch, allergens) in menu.items():
            items.append({"day_of_week": day, "meal_category": "Breakfast", "menu_item": breakfast})
            items.append({"day_of_week": day, "meal_category": "Lunch", "menu_item": lunch, "allergens": allergens})
        _insert({"doctype": "Meal Plan", "plan_name": "Standard Week", "scope": "Global", "week_type": "Weekly", "is_active": 1, "items": items})
        _insert({"doctype": "Meal Plan", "plan_name": "Allergy-Free Week", "scope": "Individual Child", "week_type": "Weekly", "is_active": 1,
                 "items": [{"day_of_week": d, "meal_category": "Lunch", "menu_item": "Rice, vegetables & chicken"} for d in menu]})
        created += 2
    created += _ensure("Transportation Route", "North Route", {
        "route_name": "North Route", "driver_name": "Driver One", "vehicle_plate": "000-TN-0000", "capacity": 12, "is_active": 1,
        "monthly_fee": 40, "stops": [{"stop_name": "City Centre", "pickup_time": "07:30:00", "dropoff_time": "17:00:00"},
                                     {"stop_name": "North Park", "pickup_time": "07:45:00", "dropoff_time": "17:15:00"}],
    })
    frappe.db.commit()
    return {"created": created}


# ── demo records (button) ────────────────────────────────────────────────────
def _registry():
    raw = frappe.db.get_default(REGISTRY_KEY)
    return json.loads(raw) if raw else []


def _save_registry(rows):
    frappe.db.set_default(REGISTRY_KEY, json.dumps(rows))


def _first(doctype, preferred, filters=None):
    if preferred and frappe.db.exists(doctype, preferred):
        return preferred
    return frappe.db.get_value(doctype, filters or {}, "name")


# Demo parent logins for the mobile app (created with the test data, removed with it).
DEMO_PASSWORD = "BabyCare@2026"
DEMO_PARENTS = (
    # first, last, relationship, mobile, app login
    ("Sara", "Ben Ali [TEST]", "Mother", "+21620111111", "sara@babycare.demo"),
    ("Karim", "Trabelsi [TEST]", "Father", "+21620222222", "karim@babycare.demo"),
    ("Amira", "Sami [TEST]", "Mother", "+21620333333", "amira@babycare.demo"),
    ("Mehdi", "Ben Ali [TEST]", "Father", "+21620444444", None),  # second parent of Adam & Lina, no app login
)


def demo_logins():
    """App logins of the installed demo parents (for the Data page and the README)."""
    out = []
    for first, last, _rel, _phone, login in DEMO_PARENTS:
        if login and frappe.db.exists("Parent Profile", {"user": login, "app_access": 1}):
            kids = frappe.get_all("Child Parent Link", filters={"parenttype": "Child", "parent_profile": frappe.db.get_value("Parent Profile", {"user": login}, "name")}, pluck="parent")
            names = [frappe.db.get_value("Child", k, "first_name") for k in kids]
            out.append({"parent": f"{first} {last.replace(' [TEST]', '')}", "login": login, "password": DEMO_PASSWORD, "children": sorted(names)})
    return out


@frappe.whitelist()
def install_test_data():
    _only_admins()
    if any(frappe.db.exists(dt, name) for dt, name in _registry() if frappe.db.exists("DocType", dt)):
        frappe.throw(_("Test data is already installed. Clear it first."))
    _save_registry([])
    install_seed_data()
    track = []
    try:
        _build_test_data(track)
    except Exception:
        _save_registry(track)
        frappe.db.commit()
        raise
    _save_registry(track)
    frappe.db.commit()
    return {"created": len(track), "logins": demo_logins()}


def _placeholder_file(track):
    f = frappe.get_doc({
        "doctype": "File",
        "file_name": "baby-care-test-document.txt",
        "is_private": 1,
        "content": b"Placeholder document created by Baby Care test data.",
    })
    f.insert(ignore_permissions=True)
    track.insert(0, ["File", f.name])
    return f.file_url


def _build_test_data(track):
    from baby_care.baby_care_management.utils.parent_access import enable_access

    parents = []
    for first, last, rel, phone, login in DEMO_PARENTS:
        for u in [login] if login else []:
            if frappe.db.exists("User", u):  # left over by an earlier demo
                if frappe.db.get_value("User", u, "user_type") == "System User":
                    frappe.throw(_("{0} is a staff account; remove it before installing demo data.").format(u))
                frappe.delete_doc("User", u, ignore_permissions=True, force=True)
        prof = _insert({"doctype": "Parent Profile", "first_name": first, "last_name": last, "relationship": rel,
                        "mobile_no": phone, "email": login, "is_active": 1, "city": "Tunis",
                        "occupation": ("Engineer", "Teacher", "Pharmacist", "Accountant")[len(parents)]}, track)
        parents.append(prof.name)
        if login:  # known password, so the mobile app can be tried at once
            enable_access(prof.name, password=DEMO_PASSWORD, login=login)
            track.append(["User", login])
    t1 = _insert({"doctype": "Teacher Profile", "full_name": "Leila Mansour [TEST]", "employment_status": "Active", "start_date": add_months(today(), -12), "email": "leila.test@example.com"}, track)
    t2 = _insert({"doctype": "Teacher Profile", "full_name": "Youssef Gharbi [TEST]", "employment_status": "Active", "start_date": add_months(today(), -6), "email": "youssef.test@example.com"}, track)
    c1 = _insert({"doctype": "Nursery Class", "class_name": "Butterflies [TEST]", "age_group": "Toddlers", "capacity": 12, "status": "Active",
                  "teachers": [{"teacher": t1.name, "is_primary": 1}]}, track)
    c2 = _insert({"doctype": "Nursery Class", "class_name": "Sunflowers [TEST]", "age_group": "Preschool", "capacity": 15, "status": "Active",
                  "teachers": [{"teacher": t2.name, "is_primary": 1}]}, track)

    kids = [
        ("Adam", "Ben Ali", add_months(today(), -30), "Male", 0, c1.name, t1.name),
        ("Lina", "Ben Ali", add_months(today(), -50), "Female", 0, c2.name, t2.name),
        ("Omar", "Trabelsi", add_months(today(), -26), "Male", 1, c1.name, t1.name),
        ("Yasmine", "Sami", add_months(today(), -44), "Female", 2, c2.name, t2.name),
        ("Rayan", "Sami", add_days(add_years(today(), -4), 5), "Male", 2, c2.name, t2.name),
    ]
    children = []
    for first, last, dob, gender, p_idx, cls, teacher in kids:
        child = _insert({
            "doctype": "Child", "first_name": first, "last_name": f"{last} [TEST]", "date_of_birth": dob, "gender": gender,
            "enrollment_status": "Active", "registration_date": add_months(today(), -3), "nursery_class": cls, "assigned_teacher": teacher,
            "parents": [{"parent_profile": parents[p_idx], "relationship": "Mother" if p_idx != 1 else "Father", "is_primary": 1, "can_pickup": 1}]
            + ([{"parent_profile": parents[3], "relationship": "Father", "is_primary": 0, "can_pickup": 1}] if p_idx == 0 else []),
            "emergency_contacts": [{"full_name": "Emergency Contact", "relationship": "Grandparent", "phone": "+21620000000"}],
            "authorized_pickups": [{"full_name": "Grandma [TEST]", "relationship": "Grandmother", "phone": "+21620000001"}],
        }, track)
        children.append(child)

    # medical records — Omar is allergic to gluten
    for child in children:
        allergies = [{"allergen": "gluten", "severity": "Severe", "reaction": "Hives", "treatment": "Antihistamine"}] if child.first_name == "Omar" else []
        _insert({"doctype": "Medical Record", "child": child.name, "record_date": today(), "blood_type": "O+",
                 "allergies": allergies, "vaccinations": [{"vaccine_name": "MMR", "date_given": add_months(today(), -10), "dose": "1", "next_due": add_months(today(), 2)}],
                 "emergency_medical_contact": "Dr. Test", "emergency_medical_phone": "+21671000000"}, track)

    # attendance for the last 10 days (weekdays)
    for i in range(10, -1, -1):
        day = getdate(add_days(today(), -i))
        if day.weekday() >= 5:
            continue
        for n, child in enumerate(children):
            absent = (i + n) % 6 == 0
            row = {"doctype": "Child Attendance", "child": child.name, "attendance_date": day, "status": "Absent" if absent else "Present"}
            if absent:
                row["absence_reason"] = "Sick"
            else:
                row.update({"check_in_time": "08:00:00"})
                if i:
                    row.update({"check_out_time": "16:30:00", "pickup_person": "Grandma [TEST]"})
            _insert(row, track)

    # documents: a birth certificate each (other mandatory documents stay
    # missing so the alerts report has something to show)
    placeholder = _placeholder_file(track)
    for child in children:
        _insert({"doctype": "Child Document", "document_for": "Child", "child": child.name, "document_type": "Birth Certificate",
                 "issue_date": child.date_of_birth, "attached_file": placeholder}, track)
    _insert({"doctype": "Child Document", "document_for": "Parent", "parent_profile": parents[0], "document_type": "Parent Identification",
             "issue_date": add_months(today(), -40), "expiry_date": add_days(today(), 20), "attached_file": placeholder}, track)

    # meal plans: Omar gets the allergy-free plan
    for child in children:
        plan = "Allergy-Free Week" if child.first_name == "Omar" else "Standard Week"
        _insert({"doctype": "Child Meal Plan", "child": child.name, "meal_plan": plan, "start_date": add_months(today(), -1), "is_active": 1}, track)

    # health incidents
    now = frappe.utils.now_datetime()
    for child, days, sev, kind, desc, action in (
        (children[0], 2, "Minor", "Injury", "Small scrape on the knee in the playground.", "Cleaned and bandaged."),
        (children[2], 5, "Moderate", "Allergic Reaction", "Mild rash after snack (checked: no gluten served).", "Antihistamine given as per medical record; parent called."),
        (children[3], 1, "Minor", "Illness", "Slight fever (37.9°C) after nap.", "Rest and water; temperature checked every hour."),
    ):
        _insert({"doctype": "Health Incident", "child": child.name, "incident_datetime": frappe.utils.add_to_date(now, days=-days, hours=-2),
                 "severity": sev, "incident_type": kind, "description": desc, "action_taken": action,
                 "notified_parent": 1, "parent_notified_at": frappe.utils.add_to_date(now, days=-days, hours=-1)}, track)

    # child-specific services
    for child, service in ((children[0], "Lunch Service"), (children[3], "Lunch Service"), (children[1], "Music Workshop"),
                           (children[4], "Extended Hours (until 18:00)")):
        if frappe.db.exists("Nursery Service", service):
            _insert({"doctype": "Child Service Assignment", "child": child.name, "service": service,
                     "start_date": add_months(today(), -1), "status": "Active"}, track)

    _insert({"doctype": "Child Transportation", "child": children[1].name, "route": "North Route", "pickup_stop": "City Centre",
             "dropoff_stop": "City Centre", "direction": "Both", "start_date": add_months(today(), -1), "is_active": 1}, track)

    # subscriptions — siblings get the family discount automatically
    plans = ["Monthly Full Day", "Quarterly Full Day", "Monthly Full Day", "Monthly Full Day", "Monthly Full Day"]
    for child, plan in zip(children, plans):
        sub = frappe.get_doc({
            "doctype": "Child Subscription", "child": child.name, "parent_profile": child.parents[0].parent_profile,
            "subscription_plan": plan, "start_date": add_months(today(), -1),
            "additional_services": [{"service": "Lunch Service"}] if child.first_name in ("Adam", "Yasmine") else [],
        })
        sub.insert(ignore_permissions=True)
        sub.submit()
        track.append([sub.doctype, sub.name])

    # invoices for the first billing period, and one payment
    from baby_care.baby_care_management.utils.billing import create_subscription_invoice

    invoices = []
    for row in [r for r in track if r[0] == "Child Subscription"]:
        inv = create_subscription_invoice(row[1], submit=1)
        track.append(["Nursery Invoice", inv])
        invoices.append(inv)
    def pay(invoice, amount, mode, ref=None):
        inv = frappe.get_doc("Nursery Invoice", invoice)
        p = frappe.get_doc({"doctype": "Nursery Payment", "parent_profile": inv.parent_profile, "amount": amount,
                            "currency": inv.currency, "mode_of_payment": mode, "payment_date": today(), "reference_no": ref,
                            "allocations": [{"invoice": inv.name, "allocated_amount": amount}]})
        p.insert(ignore_permissions=True)
        p.submit()
        track.append([p.doctype, p.name])

    first = frappe.get_doc("Nursery Invoice", invoices[0])            # Adam: paid in full
    pay(first.name, first.grand_total, "Cash")
    omar = frappe.get_doc("Nursery Invoice", invoices[2])             # Omar: partly paid
    pay(omar.name, flt(omar.grand_total / 2, 2), "Bank Transfer", "VIR-2026-0042")

    # an older one-off invoice that is now overdue (Amira's family)
    late = frappe.get_doc({"doctype": "Nursery Invoice", "parent_profile": parents[2], "child": children[3].name,
                           "posting_date": add_days(today(), -45), "due_date": add_days(today(), -15),
                           "items": [{"description": "Registration fee — Yasmine", "qty": 1, "rate": 150},
                                     {"description": "School photo pack", "qty": 1, "rate": 35}]})
    late.insert(ignore_permissions=True)
    late.submit()
    track.append([late.doctype, late.name])


@frappe.whitelist()
def clear_test_data():
    _only_admins()
    return _clear_tracked()


def _clear_tracked():
    rows = _registry()
    removed = 0
    for doctype, name in reversed(rows):
        if not frappe.db.exists("DocType", doctype) or not frappe.db.exists(doctype, name):
            continue
        if doctype == "Nursery Invoice":
            # payments recorded on demo invoices (by users trying the app) go too;
            # cancelling them updates the invoice, so load it only afterwards
            for pe in set(frappe.get_all("Nursery Payment Allocation", filters={"invoice": name, "parenttype": "Nursery Payment"}, pluck="parent")):
                if not frappe.db.exists("Nursery Payment", pe):
                    continue
                pe_doc = frappe.get_doc("Nursery Payment", pe)
                if pe_doc.docstatus == 1:
                    pe_doc.flags.ignore_permissions = True
                    pe_doc.flags.ignore_links = True
                    pe_doc.cancel()
                frappe.delete_doc("Nursery Payment", pe, ignore_permissions=True, force=True)
        if doctype == "User":
            frappe.db.delete("Parent App Device", {"user": name})
        doc = frappe.get_doc(doctype, name)
        if doc.docstatus == 1:
            doc.flags.ignore_permissions = True
            # demo invoices and subscriptions reference each other; the whole
            # tracked set is being removed, so skip the back-link check
            doc.flags.ignore_links = True
            doc.cancel()
        frappe.delete_doc(doctype, name, ignore_permissions=True, force=True, ignore_on_trash=False)
        removed += 1
    frappe.db.set_default(REGISTRY_KEY, "")
    frappe.db.commit()
    return {"removed": removed}


@frappe.whitelist()
def get_status():
    _only_admins()
    counts = {}
    for dt in ("Parent Profile", "Child", "Teacher Profile", "Nursery Class", "Child Subscription", "Child Attendance", "Medical Record", "Health Incident",
               "Child Document", "Child Meal Plan", "Child Service Assignment", "Child Transportation", "Nursery Invoice", "Nursery Payment",
               "Subscription Plan", "Nursery Service", "Meal Plan", "Transportation Route", "Age Group", "Attendance Status", "Document Type Config"):
        counts[dt] = frappe.db.count(dt)
    test = {}
    for dt, _name in _registry():
        test[dt] = test.get(dt, 0) + 1
    return {"counts": counts, "test_data": test, "test_installed": bool(test), "logins": demo_logins()}
