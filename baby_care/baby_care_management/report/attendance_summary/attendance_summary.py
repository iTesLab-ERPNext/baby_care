import frappe
from frappe import _


def execute(filters=None):
    filters = frappe._dict(filters or {})
    f = {"attendance_date": ("between", [filters.from_date, filters.to_date])}
    for key in ("child", "nursery_class", "status"):
        if filters.get(key):
            f[key] = filters[key]
    rows = frappe.get_list(
        "Child Attendance",
        filters=f,
        fields=["name", "attendance_date", "child", "nursery_class", "status", "check_in_time", "check_out_time", "pickup_person", "absence_reason", "recorded_by"],
        order_by="attendance_date desc, child asc",
        limit_page_length=0,
    )
    names = {c.name: c.full_name for c in frappe.get_list("Child", filters={"name": ("in", list({r.child for r in rows}) or [""])}, fields=["name", "full_name"], limit_page_length=0)}
    types = dict(frappe.get_all("Attendance Status", fields=["name", "status_type"], as_list=True))
    for r in rows:
        r.child_name = names.get(r.child, r.child)
        r.status_type = types.get(r.status)

    if filters.get("group_by_child"):
        return _per_child(rows)

    columns = [
        {"label": _("Date"), "fieldname": "attendance_date", "fieldtype": "Date", "width": 100},
        {"label": _("Child"), "fieldname": "child", "fieldtype": "Link", "options": "Child", "width": 120},
        {"label": _("Name"), "fieldname": "child_name", "fieldtype": "Data", "width": 170},
        {"label": _("Class"), "fieldname": "nursery_class", "fieldtype": "Link", "options": "Nursery Class", "width": 130},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Link", "options": "Attendance Status", "width": 90},
        {"label": _("Check-in"), "fieldname": "check_in_time", "fieldtype": "Time", "width": 90},
        {"label": _("Check-out"), "fieldname": "check_out_time", "fieldtype": "Time", "width": 90},
        {"label": _("Picked up by"), "fieldname": "pickup_person", "fieldtype": "Data", "width": 140},
        {"label": _("Absence Reason"), "fieldname": "absence_reason", "fieldtype": "Data", "width": 140},
        {"label": _("Recorded By"), "fieldname": "recorded_by", "fieldtype": "Link", "options": "User", "width": 140},
    ]
    present = len([r for r in rows if r.status_type in ("Present", "Late")])
    absent = len([r for r in rows if r.status_type in ("Absent", "Leave")])
    by_day = {}
    for r in rows:
        d = str(r.attendance_date)
        by_day.setdefault(d, [0, 0])
        if r.status_type in ("Present", "Late"):
            by_day[d][0] += 1
        elif r.status_type in ("Absent", "Leave"):
            by_day[d][1] += 1
    days = sorted(by_day)
    chart = {"data": {"labels": days, "datasets": [{"name": _("Present"), "values": [by_day[d][0] for d in days]}, {"name": _("Absent"), "values": [by_day[d][1] for d in days]}]}, "type": "bar"}
    summary = [
        {"label": _("Records"), "value": len(rows), "indicator": "Blue"},
        {"label": _("Present / Late"), "value": present, "indicator": "Green"},
        {"label": _("Absent / Leave"), "value": absent, "indicator": "Red"},
        {"label": _("Attendance rate"), "value": f"{(present * 100 // (present + absent)) if (present + absent) else 0}%", "indicator": "Blue"},
    ]
    return columns, rows, None, chart, summary


def _per_child(rows):
    agg = {}
    for r in rows:
        a = agg.setdefault(r.child, {"child": r.child, "child_name": r.child_name, "nursery_class": r.nursery_class, "present": 0, "absent": 0, "late": 0, "total": 0})
        a["total"] += 1
        if r.status_type == "Present":
            a["present"] += 1
        elif r.status_type == "Late":
            a["late"] += 1
            a["present"] += 1
        elif r.status_type in ("Absent", "Leave"):
            a["absent"] += 1
    data = sorted(agg.values(), key=lambda x: x["child_name"] or "")
    for d in data:
        d["rate"] = round(d["present"] * 100.0 / d["total"], 1) if d["total"] else 0
    columns = [
        {"label": _("Child"), "fieldname": "child", "fieldtype": "Link", "options": "Child", "width": 120},
        {"label": _("Name"), "fieldname": "child_name", "fieldtype": "Data", "width": 180},
        {"label": _("Class"), "fieldname": "nursery_class", "fieldtype": "Link", "options": "Nursery Class", "width": 130},
        {"label": _("Days Recorded"), "fieldname": "total", "fieldtype": "Int", "width": 110},
        {"label": _("Present"), "fieldname": "present", "fieldtype": "Int", "width": 90},
        {"label": _("Late"), "fieldname": "late", "fieldtype": "Int", "width": 80},
        {"label": _("Absent"), "fieldname": "absent", "fieldtype": "Int", "width": 90},
        {"label": _("Attendance %"), "fieldname": "rate", "fieldtype": "Percent", "width": 110},
    ]
    return columns, data
