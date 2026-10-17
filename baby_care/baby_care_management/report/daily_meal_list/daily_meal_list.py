import frappe
from frappe import _
from frappe.utils import getdate, today

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def execute(filters=None):
    filters = frappe._dict(filters or {})
    date = getdate(filters.get("date") or today())
    day = DAYS[date.weekday()]
    cf = {"enrollment_status": "Active"}
    if filters.get("nursery_class"):
        cf["nursery_class"] = filters.nursery_class
    children = {c.name: c for c in frappe.get_list("Child", filters=cf, fields=["name", "full_name", "nursery_class", "has_allergies"], limit_page_length=0)}
    plans = {}
    if children:
        for p in frappe.get_list("Child Meal Plan", filters={"child": ("in", list(children)), "is_active": 1}, fields=["child", "meal_plan", "dietary_notes", "start_date", "end_date"], limit_page_length=0):
            if (p.start_date and getdate(p.start_date) > date) or (p.end_date and getdate(p.end_date) < date):
                continue
            plans[p.child] = p
    default_plan = frappe.db.get_value("Meal Plan", {"scope": "Global", "is_active": 1}, "name")
    order = dict(frappe.get_all("Meal Category", fields=["name", "sort_order"], as_list=True))
    menus = {}
    rows = []
    for child in sorted(children.values(), key=lambda c: (c.nursery_class or "", c.full_name or "")):
        cp = plans.get(child.name)
        plan = cp.meal_plan if cp else default_plan
        if not plan:
            rows.append({"child": child.name, "child_name": child.full_name, "nursery_class": child.nursery_class, "menu_item": _("No meal plan assigned")})
            continue
        if plan not in menus:
            menus[plan] = frappe.get_all("Meal Plan Item", filters={"parent": plan, "parenttype": "Meal Plan", "day_of_week": day}, fields=["meal_category", "menu_item", "allergens", "notes"])
        for item in sorted(menus[plan], key=lambda i: order.get(i.meal_category, 99)):
            rows.append({"child": child.name, "child_name": child.full_name, "nursery_class": child.nursery_class, "meal_plan": plan,
                         "meal_category": item.meal_category, "menu_item": item.menu_item, "allergens": item.allergens,
                         "allergy_alert": 1 if child.has_allergies else 0, "notes": (cp.dietary_notes if cp else "") or item.notes})
    columns = [
        {"label": _("Class"), "fieldname": "nursery_class", "fieldtype": "Link", "options": "Nursery Class", "width": 130},
        {"label": _("Child"), "fieldname": "child", "fieldtype": "Link", "options": "Child", "width": 120},
        {"label": _("Name"), "fieldname": "child_name", "fieldtype": "Data", "width": 170},
        {"label": _("Meal"), "fieldname": "meal_category", "fieldtype": "Link", "options": "Meal Category", "width": 120},
        {"label": _("Menu"), "fieldname": "menu_item", "fieldtype": "Data", "width": 200},
        {"label": _("Allergens"), "fieldname": "allergens", "fieldtype": "Data", "width": 120},
        {"label": _("Allergy Alert"), "fieldname": "allergy_alert", "fieldtype": "Check", "width": 100},
        {"label": _("Plan"), "fieldname": "meal_plan", "fieldtype": "Link", "options": "Meal Plan", "width": 140},
        {"label": _("Notes"), "fieldname": "notes", "fieldtype": "Data", "width": 180},
    ]
    return columns, rows, _("Menu for {0}, {1}").format(_(day), date)
