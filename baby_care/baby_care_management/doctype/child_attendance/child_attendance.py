import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today


class ChildAttendance(Document):
    def validate(self):
        self._prevent_duplicate()
        self._validate_times()

    def _prevent_duplicate(self):
        existing = frappe.db.exists(
            "Child Attendance",
            {"child": self.child, "attendance_date": self.attendance_date, "name": ("!=", self.name)},
        )
        if existing:
            frappe.throw(
                _("Attendance for {0} on {1} already recorded (ref: {2}).").format(
                    self.child, self.attendance_date, existing
                )
            )

    def _validate_times(self):
        if self.check_in_time and self.check_out_time:
            if self.check_out_time < self.check_in_time:
                frappe.throw(_("Check-out time cannot be before check-in time."))
