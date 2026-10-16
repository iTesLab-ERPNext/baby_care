import frappe
from frappe import _
from frappe.model.document import Document


class NurseryClass(Document):
    def validate(self):
        self._update_enrollment_count()
        self._check_capacity()

    def _update_enrollment_count(self):
        active = [c for c in (self.children or []) if c.enrollment_status == "Active"]
        self.current_enrollment = len(active)

    def _check_capacity(self):
        settings = frappe.get_single("Nursery Settings")
        if settings.enforce_class_capacity and self.capacity:
            if self.current_enrollment > self.capacity:
                frappe.throw(
                    _("Class {0} is at capacity ({1}/{2}). Cannot add more children.").format(
                        self.class_name, self.current_enrollment, self.capacity
                    )
                )
