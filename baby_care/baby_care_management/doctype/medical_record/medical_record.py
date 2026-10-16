import frappe
from frappe import _
from frappe.model.document import Document


class MedicalRecord(Document):
    def validate(self):
        # Ensure child is enrolled
        if self.child:
            status = frappe.db.get_value("Child", self.child, "enrollment_status")
            if status == "Withdrawn":
                frappe.msgprint(
                    _("Warning: This child has Withdrawn status. Saving medical record anyway."),
                    alert=True
                )
        # Update child flags
        self._update_child_flags()

    def _update_child_flags(self):
        if not self.child:
            return
        has_allergies = 1 if self.allergies else 0
        has_chronic = 1 if self.chronic_conditions else 0
        frappe.db.set_value(
            "Child", self.child,
            {"has_allergies": has_allergies, "has_chronic_condition": has_chronic},
            update_modified=False,
        )
