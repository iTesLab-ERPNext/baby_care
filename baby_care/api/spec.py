"""
Single source of truth for the Parent API documentation.

Used by:
* ``baby_care.api.v1.openapi``      → OpenAPI 3 JSON (Swagger UI, Postman, …)
* ``/parent-api`` (public/parent-api/index.html) → human-readable docs + "Try it"
"""

BASE = "/api/method/baby_care.api.v1."
VERSION = "2.0.0"

DATE = {"type": "string", "format": "date"}

CHILD = ("child", "string", True, "Child ID (from `children`)", "CHILD-00001")
LIMIT = ("limit", "integer", False, "Page size (default 20, max 100)", 20)
START = ("start", "integer", False, "Offset for pagination (default 0)", 0)

# name, method, tag, summary, description, auth, params[(name, type, required, description, example)], example response
ENDPOINTS = [
    ("app_login", "POST", "Mobile App", "Mobile login (token)",
     "Login for the mobile app. Returns a token to send on every call as `Authorization: token <token>` — no cookie or CSRF "
     "token needed. The token stays valid until the parent changes their password, the nursery sets a new one, or "
     "`app_logout` is called with `all_devices=1`. Limited to 10 attempts per 5 minutes per IP.",
     False,
     [("usr", "string", True, "Parent e-mail (the login set on the Parent Profile's Parent App tab)", "parent@example.com"),
      ("pwd", "string", True, "Password", "********"),
      ("device_name", "string", False, "Phone name, for the nursery's records", "Pixel 9")],
     {"token": "1a2b3c4d5e6f7a8:9b8c7d6e5f4a3b2", "user": "parent@example.com", "full_name": "Sara Ben Ali",
      "parents": [{"parent": "PAR-00001", "full_name": "Sara Ben Ali", "relationship": "Mother"}],
      "children": [{"child": "CHILD-00001", "full_name": "Adam Ben Ali"}],
      "app": {"name": "My Nursery", "currency": "TND", "api_version": "2.0.0", "push_enabled": True}}),
    ("app_logout", "POST", "Mobile App", "Mobile logout",
     "Removes this phone's push registration. With `all_devices=1` every app token of the parent stops working.", True,
     [("push_token", "string", False, "This phone's Expo push token", "ExponentPushToken[xxxx]"),
      ("all_devices", "integer", False, "1 = sign out on every phone", 0)], {"ok": True}),
    ("change_password", "POST", "Mobile App", "Change password",
     "The parent changes their own password. Returns a new token; other phones are signed out.", True,
     [("old_password", "string", True, "Current password", "********"),
      ("new_password", "string", True, "New password (8+ characters)", "********")],
     {"ok": True, "token": "1a2b3c4d5e6f7a8:new-secret"}),
    ("app_info", "GET", "Mobile App", "App information",
     "Public: the nursery name the app shows on its login screen, currency and API version.", False, [],
     {"name": "My Nursery", "facility_type": "Nursery", "logo": "/assets/baby_care/images/baby_care_logo.svg",
      "currency": "TND", "api_version": "2.0.0", "push_enabled": True}),
    ("register_device", "POST", "Mobile App", "Register for push notifications",
     "Stores the phone's Expo push token. The nursery then pushes arrivals, departures, health notes, new invoices and payments.", True,
     [("push_token", "string", True, "Expo push token", "ExponentPushToken[xxxx]"),
      ("platform", "string", False, "ios, android or web", "android"),
      ("device_name", "string", False, "Phone name", "Pixel 9"),
      ("app_version", "string", False, "App version", "1.0.0")], {"ok": True}),
    ("notifications", "GET", "Mobile App", "Notifications feed",
     "Recent activity for the parent's family, newest first: arrivals, departures, absences, health notes, new and overdue "
     "invoices, payments, missing documents, subscriptions ending soon and messages from the nursery.", True,
     [("days", "integer", False, "How far back (default 30, max 180)", 30), LIMIT, START],
     [{"id": "check_in:ATT-0001", "type": "check_in", "datetime": "2026-11-26 08:02:00", "title": "Adam has arrived",
       "body": "Checked in at 08:02", "child": "CHILD-00001", "child_name": "Adam", "ref": "ATT-0001"}]),
    ("login", "POST", "Authentication", "Log in a parent",
     "Checks the parent's e-mail and password, starts a session and returns the session id (`sid`) and a CSRF token. "
     "Browsers keep the `sid` cookie automatically; mobile apps send it back as a `Cookie: sid=…` header. "
     "Only accounts linked to a parent profile can log in. Limited to 10 attempts per 5 minutes per IP.",
     False,
     [("usr", "string", True, "Parent e-mail / user id", "parent@example.com"),
      ("pwd", "string", True, "Password", "********")],
     {"user": "parent@example.com", "full_name": "Sara Ben Ali", "sid": "4b1c…", "csrf_token": "f2e9…",
      "parents": [{"parent": "PAR-00001", "full_name": "Sara Ben Ali", "relationship": "Mother"}],
      "children": [{"child": "CHILD-00001", "full_name": "Adam Ben Ali"}]}),
    ("logout", "POST", "Authentication", "Log out", "Ends the current session.", True, [], {"ok": True}),
    ("me", "GET", "Profile", "Parent profile", "The logged-in parent, their parent profile(s) and a short list of children.", True, [],
     {"user": "parent@example.com", "full_name": "Sara Ben Ali",
      "parents": [{"parent": "PAR-00001", "full_name": "Sara Ben Ali", "relationship": "Mother", "mobile_no": "+216…", "email": "parent@example.com"}],
      "children": [{"child": "CHILD-00001", "full_name": "Adam Ben Ali"}]}),
    ("children", "GET", "Children", "List my children", "All children linked to the parent, with class, teacher and status.", True, [],
     [{"child": "CHILD-00001", "full_name": "Adam Ben Ali", "date_of_birth": "2024-04-02", "age": "2 yr 6 mo", "gender": "Male",
       "enrollment_status": "Active", "nursery_class": "Butterflies", "teacher": "Leila Mansour", "relationship": "Mother",
       "subscription_status": "Active", "has_allergies": 0, "photo": None}]),
    ("child", "GET", "Children", "Child profile",
     "Full profile of one child: class and teachers, emergency contacts, authorized pickup people, allergies, vaccinations and current subscription.",
     True, [CHILD],
     {"child": "CHILD-00001", "full_name": "Adam Ben Ali", "nursery_class": "Butterflies", "teachers": ["Leila Mansour"],
      "emergency_contacts": [{"full_name": "…", "relationship": "Grandparent", "phone": "+216…"}],
      "authorized_pickups": [{"full_name": "Grandma", "relationship": "Grandmother", "phone": "+216…"}],
      "allergies": [{"allergen": "gluten", "severity": "Severe"}],
      "vaccinations": [{"vaccine_name": "MMR", "date_given": "2025-12-01", "next_due": "2026-12-01"}],
      "subscription": {"name": "SUB-…", "plan": "Monthly Full Day", "status": "Active", "end_date": "2027-09-30"}}),
    ("child_tracking", "GET", "Follow-up", "Daily follow-up (suivi)",
     "Everything a parent wants at a glance for one day: attendance (arrival, departure, who picked up), today's menu, "
     "recent health incidents, the last-30-days attendance rate, upcoming vaccinations, document alerts and subscription status.",
     True, [CHILD, ("date", "string", False, "Day to report (YYYY-MM-DD, default today)", "2026-11-02")],
     {"child": "CHILD-00001", "date": "2026-11-02",
      "attendance": {"status": "Present", "check_in_time": "08:02:00", "check_out_time": None, "picked_up_by": None},
      "meals": [{"meal_category": "Breakfast", "menu_item": "Porridge"}, {"meal_category": "Lunch", "menu_item": "Chicken & rice"}],
      "recent_incidents": [], "attendance_30_days": {"present": 18, "absent": 2, "rate": 90.0},
      "upcoming_vaccinations": [{"vaccine_name": "MMR", "next_due": "2026-12-01"}],
      "document_alerts": [{"document_type": "Vaccination Card", "status": "Missing"}],
      "subscription": {"status": "Active", "end_date": "2027-09-30", "next_billing_date": "2026-12-01"}}),
    ("child_attendance", "GET", "Follow-up", "Attendance history", "Attendance records of one child, newest first.", True,
     [CHILD, ("from_date", "string", False, "Start date (default 30 days ago)", "2026-10-01"),
      ("to_date", "string", False, "End date (default today)", "2026-11-02"), LIMIT, START],
     {"summary": {"present": 18, "absent": 2, "late": 1, "rate": 90.0},
      "records": [{"date": "2026-11-02", "status": "Present", "check_in_time": "08:02:00", "check_out_time": "16:30:00",
                   "picked_up_by": "Grandma", "absence_reason": None}]}),
    ("child_meals", "GET", "Follow-up", "Menu of the day",
     "The child's menu for a day: their own meal plan if one is assigned, otherwise the nursery's global menu.", True,
     [CHILD, ("date", "string", False, "Day (default today)", "2026-11-02")],
     {"date": "2026-11-02", "day": "Monday", "meal_plan": "Standard Week", "dietary_notes": None,
      "items": [{"meal_category": "Lunch", "menu_item": "Chicken & rice", "allergens": "gluten"}]}),
    ("child_incidents", "GET", "Follow-up", "Health incidents", "Health incidents recorded for the child, newest first.", True,
     [CHILD, LIMIT, START],
     [{"datetime": "2026-10-20 10:15:00", "severity": "Minor", "incident_type": "Injury", "description": "Scraped knee",
       "action_taken": "Cleaned and bandaged", "parent_notified": 1}]),
    ("child_documents", "GET", "Follow-up", "Documents status",
     "Documents on file for the child (status and expiry) and mandatory documents still missing.", True, [CHILD],
     {"documents": [{"document_type": "Birth Certificate", "status": "Valid", "issue_date": "2024-04-02", "expiry_date": None}],
      "missing": ["Vaccination Card", "Enrollment Form"]}),
    ("subscriptions", "GET", "Billing", "Subscriptions", "Subscriptions of all my children (or one child).", True,
     [("child", "string", False, "Only this child", "CHILD-00001")],
     [{"name": "SUB-CHILD-00001-0001", "child": "CHILD-00001", "child_name": "Adam Ben Ali", "plan": "Monthly Full Day",
       "status": "Active", "start_date": "2026-10-01", "end_date": "2027-09-30", "next_billing_date": "2026-12-01",
       "amount_per_period": 410.0, "discount_percent": 0, "currency": "TND"}]),
    ("invoices", "GET", "Billing", "Invoices", "Submitted invoices of the parent, newest first.", True,
     [("status", "string", False, "`all` (default), `unpaid`, `overdue` or `paid`", "unpaid"),
      ("child", "string", False, "Only this child", "CHILD-00001"), LIMIT, START],
     [{"name": "INV-2026-00001", "date": "2026-10-01", "due_date": "2026-10-16", "child": "CHILD-00001",
       "billing_period": "2026-10", "grand_total": 410.0, "outstanding_amount": 410.0, "status": "Unpaid", "currency": "TND"}]),
    ("invoice", "GET", "Billing", "Invoice details", "One invoice with its lines, taxes and payments.", True,
     [("name", "string", True, "Invoice number", "INV-2026-00001")],
     {"name": "INV-2026-00001", "grand_total": 410.0, "outstanding_amount": 0.0, "status": "Paid",
      "items": [{"description": "Monthly Full Day — Adam — 2026-10-01 to 2026-10-31", "qty": 1, "rate": 350.0, "amount": 350.0}],
      "taxes": [], "payments": [{"payment": "PAY-2026-00001", "date": "2026-10-05", "amount": 410.0}]}),
    ("payments", "GET", "Billing", "Payments", "Payments received from the parent, newest first, with the invoices they settle.", True,
     [LIMIT, START],
     [{"name": "PAY-2026-00001", "date": "2026-10-05", "amount": 410.0, "mode_of_payment": "Cash", "reference_no": None,
       "currency": "TND", "invoices": [{"invoice": "INV-2026-00001", "allocated_amount": 410.0}]}]),
    ("balance", "GET", "Billing", "Account balance", "Totals for the parent: invoiced, paid, outstanding, overdue and the next due date, overall and per child.", True, [],
     {"currency": "TND", "invoiced": 1520.0, "paid": 1110.0, "outstanding": 410.0, "overdue": 0.0, "credit": 0.0, "next_due_date": "2026-11-16",
      "by_child": [{"child": "CHILD-00001", "child_name": "Adam Ben Ali", "invoiced": 820.0, "outstanding": 410.0}]}),
]


def openapi(server=""):
    paths = {}
    for name, method, tag, summary, description, auth, params, example in ENDPOINTS:
        op = {
            "tags": [tag],
            "summary": summary,
            "description": description,
            "operationId": name,
            "responses": {
                "200": {"description": "OK — the result is wrapped in `message`.",
                        "content": {"application/json": {"example": {"message": example}}}},
                "401": {"description": "Wrong e-mail or password (login)"},
                "403": {"description": "Not logged in, or the account is not linked to a parent profile"},
                "404": {"description": "Record not found (or not one of your children)"},
                "417": {"description": "Invalid or missing parameter"},
                "429": {"description": "Too many login attempts"},
            },
        }
        if not auth:
            op["security"] = []
        if method == "GET":
            op["parameters"] = [
                {"name": p[0], "in": "query", "required": p[2], "description": p[3],
                 "schema": {"type": p[1]}, "example": p[4]}
                for p in params
            ]
        elif params:
            op["requestBody"] = {"required": True, "content": {"application/json": {"schema": {
                "type": "object",
                "required": [p[0] for p in params if p[2]],
                "properties": {p[0]: {"type": p[1], "description": p[3], "example": p[4]} for p in params},
            }}}}
        paths[f"{BASE}{name}"] = {method.lower(): op}
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Baby Care — Parent API",
            "version": VERSION,
            "description": (
                "Read-only API for parents: their children, daily follow-up, invoices and payments. "
                "Every call returns only the logged-in parent's own data.\n\n"
                "**Authentication** — call `login`, then send the session cookie (`sid`). "
                "For POST calls made with a browser session also send the `X-Frappe-CSRF-Token` header returned by `login`. "
                "Server-to-server clients can use Frappe API keys instead: `Authorization: token <api_key>:<api_secret>`."
            ),
        },
        "servers": [{"url": server or "/"}],
        "components": {"securitySchemes": {
            "session": {"type": "apiKey", "in": "cookie", "name": "sid"},
            "token": {"type": "apiKey", "in": "header", "name": "Authorization", "description": "token <api_key>:<api_secret>"},
        }},
        "security": [{"session": []}, {"token": []}],
        "tags": [{"name": t} for t in dict.fromkeys(e[2] for e in ENDPOINTS)],
        "paths": paths,
    }
