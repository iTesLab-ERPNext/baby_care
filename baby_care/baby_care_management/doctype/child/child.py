import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, date_diff, today


class Child(Document):
    def autoname(self):
        self.full_name = f"{self.first_name} {self.last_name}".strip()
        self.name = self.full_name

    def validate(self):
        self._set_full_name()
        self._set_age_display()
        self._validate_parents()
        self._validate_enrollment()

    def _set_full_name(self):
        self.full_name = f"{self.first_name} {self.last_name}".strip()

    def _set_age_display(self):
        if self.date_of_birth:
            dob = getdate(self.date_of_birth)
            today_date = getdate(today())
            total_months = (today_date.year - dob.year) * 12 + (today_date.month - dob.month)
            years = total_months // 12
            months = total_months % 12
            if years > 0:
                self.age_display = f"{years} yr {months} mo"
            else:
                self.age_display = f"{months} mo"

    def _validate_parents(self):
        if not self.parents:
            frappe.throw(_("A child must have at least one parent or guardian linked."))
        primary = [p for p in self.parents if p.is_primary]
        if not primary:
            # auto-mark first as primary
            self.parents[0].is_primary = 1

    def _validate_enrollment(self):
        if self.enrollment_status == "Active" and not self.registration_date:
            frappe.throw(_("Registration date is required for an active enrollment."))

    @frappe.whitelist()
    def get_attendance_summary(self):
        return frappe.db.sql("""
            SELECT
                attendance_date,
                status,
                check_in_time,
                check_out_time
            FROM `tabChild Attendance`
            WHERE child = %(child)s
            ORDER BY attendance_date DESC
            LIMIT 30
        """, {"child": self.name}, as_dict=True)
