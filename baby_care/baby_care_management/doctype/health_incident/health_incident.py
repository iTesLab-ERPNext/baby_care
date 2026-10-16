import frappe
from frappe import _
from frappe.model.document import Document


class HealthIncident(Document):
    def validate(self):
        if self.severity == "Emergency" and not self.notified_parent:
            frappe.msgprint(
                _("Emergency incident — please ensure the parent has been notified."),
                alert=True,
                indicator="red",
            )
