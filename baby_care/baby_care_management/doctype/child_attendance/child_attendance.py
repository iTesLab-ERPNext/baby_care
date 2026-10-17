from datetime import date, datetime

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_time, getdate, nowtime, today


class ChildAttendance(Document):
    def validate(self):
        if getdate(self.attendance_date) > getdate(today()):
            frappe.throw(_("Attendance cannot be recorded for a future date."))
        if not self.recorded_by:
            self.recorded_by = frappe.session.user
        if not self.nursery_class:
            self.nursery_class = frappe.db.get_value("Child", self.child, "nursery_class")
        self._prevent_duplicate()
        self._clear_default_times()
        self._validate_status()
        self._validate_times()
        self._verify_pickup()

    def _prevent_duplicate(self):
        existing = frappe.db.exists(
            "Child Attendance",
            {"child": self.child, "attendance_date": self.attendance_date, "name": ("!=", self.name)},
        )
        if existing:
            frappe.throw(_("Attendance for {0} on {1} is already recorded ({2}).").format(self.child, self.attendance_date, existing))

    def _status_type(self):
        return frappe.db.get_value("Attendance Status", self.status, "status_type") if self.status else None

    def _clear_default_times(self):
        """Frappe pre-fills every empty Time field with the current time
        (server and client). Drop values that cannot be real."""
        if self._status_type() in ("Absent", "Leave", "Holiday"):
            self.check_in_time = None
            self.check_out_time = None
            self.pickup_person = None
            return
        if self.is_new() and self.check_out_time and not self.pickup_person:
            now = datetime.combine(date.today(), get_time(nowtime()))
            out = datetime.combine(date.today(), get_time(self.check_out_time))
            if abs((now - out).total_seconds()) < 120:
                self.check_out_time = None

    def _validate_status(self):
        stype = self._status_type()
        if stype == "Absent" and not self.absence_reason:
            frappe.msgprint(_("Consider recording an absence reason."), alert=True)

    def _validate_times(self):
        if self.check_out_time and not self.check_in_time:
            frappe.throw(_("Check-in time is required before check-out."))
        if self.check_in_time and self.check_out_time and get_time(self.check_out_time) < get_time(self.check_in_time):
            frappe.throw(_("Check-out time cannot be before check-in time."))

    def _verify_pickup(self):
        if not self.check_out_time:
            return
        if not cint(frappe.db.get_single_value("Nursery Settings", "enforce_pickup_verification")):
            return
        if not self.pickup_person:
            frappe.throw(_("Record who picked the child up."))
        if self.pickup_person.strip().lower() not in [n.lower() for n in authorized_pickup_names(self.child)]:
            frappe.throw(_("{0} is not an authorized pickup person for {1}.").format(self.pickup_person, self.child))


@frappe.whitelist()
def get_authorized_pickups(child):
    frappe.has_permission("Child", "read", child, throw=True)
    return authorized_pickup_names(child)


def authorized_pickup_names(child):
    names = frappe.get_all("Child Authorized Pickup", filters={"parent": child, "parenttype": "Child"}, pluck="full_name")
    for row in frappe.get_all(
        "Child Parent Link", filters={"parent": child, "parenttype": "Child"}, fields=["parent_customer", "can_pickup", "is_primary"]
    ):
        if row.can_pickup or row.is_primary:
            names.append(frappe.db.get_value("Customer", row.parent_customer, "customer_name") or row.parent_customer)
    return [n.strip() for n in names if n]


@frappe.whitelist()
def mark_class_attendance(nursery_class, attendance_date=None, status="Present"):
    """Bulk-create attendance rows for every active child of a class (skips existing)."""
    attendance_date = attendance_date or today()
    frappe.has_permission("Child Attendance", "create", throw=True)
    children = frappe.get_list("Child", filters={"nursery_class": nursery_class, "enrollment_status": "Active"}, pluck="name")
    created = 0
    for child in children:
        if frappe.db.exists("Child Attendance", {"child": child, "attendance_date": attendance_date}):
            continue
        doc = frappe.get_doc({"doctype": "Child Attendance", "child": child, "attendance_date": attendance_date,
                              "status": status, "nursery_class": nursery_class})
        if status == "Present":
            doc.check_in_time = frappe.utils.nowtime()
        doc.insert()
        created += 1
    return created
