import frappe
from frappe import _
from frappe.model.document import Document


class TeacherProfile(Document):
    def validate(self):
        if self.employment_status == "Active" and self.end_date:
            frappe.throw(_("An active teacher cannot have an end date."))
