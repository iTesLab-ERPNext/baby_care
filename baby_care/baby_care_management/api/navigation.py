"""
Navbar menu: the workspace sections (setup/desk.py SECTIONS) as a
permission-filtered tree with ready-to-use routes. Sent to the browser in
the boot payload, so the menu costs no extra request and never lists a page
the user cannot open.
"""
import frappe
from frappe.utils import cint

from baby_care.baby_care_management.setup.desk import DASHBOARD, SECTIONS, WORKSPACE


def _slug(name):
    return name.lower().replace("_", "-").replace(" ", "-")


def _route(link_to, link_type):
    if link_type == "DocType":
        return f"/app/{_slug(link_to)}"
    if link_type == "Report":
        report_type = frappe.db.get_value("Report", link_to, "report_type")
        if report_type in ("Script Report", "Query Report"):
            return f"/app/query-report/{link_to}"
        ref = frappe.db.get_value("Report", link_to, "ref_doctype")
        return f"/app/{_slug(ref)}/view/report/{link_to}"
    if link_type == "Page":
        return f"/app/{link_to}"
    if link_type == "Dashboard":
        return f"/app/dashboard-view/{link_to}"
    return None


def _allowed(link_to, link_type, cache):
    key = (link_type, link_to)
    if key in cache:
        return cache[key]
    ok = False
    try:
        if link_type == "DocType":
            meta = frappe.db.get_value("DocType", link_to, ["istable"], as_dict=True)
            ok = bool(meta) and not cint(meta.istable) and frappe.has_permission(link_to, "read")
        elif link_type == "Report":
            ok = bool(frappe.db.exists("Report", {"name": link_to, "disabled": 0})) and frappe.get_cached_doc("Report", link_to).is_permitted()
        elif link_type == "Page":
            ok = bool(frappe.db.exists("Page", link_to)) and frappe.get_cached_doc("Page", link_to).is_permitted()
        elif link_type == "Dashboard":
            ok = bool(frappe.db.exists("Dashboard", link_to))
    except Exception:
        ok = False
    cache[key] = bool(ok)
    return cache[key]


def get_menu(user=None):
    """{"workspace": {...}, "sections": [{label, items: [{label, route, kind}]}]} or None."""
    user = user or frappe.session.user
    if user == "Guest":
        return None
    from baby_care.baby_care_management.utils.permissions import has_app_permission

    original = frappe.session.user
    if user != original:
        frappe.set_user(user)
    try:
        if not has_app_permission():
            return None
        cache = {}
        sections = []
        for title, items in SECTIONS:
            rows = [
                {"label": label, "route": _route(link_to, link_type), "kind": link_type}
                for label, link_to, link_type in items
                if _allowed(link_to, link_type, cache)
            ]
            if title == "Dashboard" and _allowed(DASHBOARD, "Dashboard", cache):
                rows.insert(0, {"label": DASHBOARD, "route": _route(DASHBOARD, "Dashboard"), "kind": "Dashboard"})
            if rows:
                sections.append({"label": title, "items": rows})
        if not sections:
            return None
        return {"workspace": {"label": WORKSPACE, "route": "/app/" + _slug(WORKSPACE)}, "sections": sections}
    finally:
        if user != original:
            frappe.set_user(original)


@frappe.whitelist()
def get_navbar_menu():
    return get_menu()
