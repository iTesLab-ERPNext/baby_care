import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime


class HealthIncident(Document):
    def validate(self):
        if not self.recorded_by:
            self.recorded_by = frappe.session.user
        if self.incident_datetime and get_datetime(self.incident_datetime) > now_datetime():
            frappe.throw(_("Incident time cannot be in the future."))
        if self.notified_parent and not self.parent_notified_at:
            self.parent_notified_at = now_datetime()
        if not self.notified_parent:
            self.parent_notified_at = None
        if self.severity in ("Serious", "Emergency") and not self.action_taken:
            frappe.throw(_("Action taken is required for serious and emergency incidents."))

    def after_insert(self):
        if self.severity in ("Serious", "Emergency"):
            from baby_care.baby_care_management.utils.notifications import notify_roles

            notify_roles(
                ["Nursery Administrator", "Nursery Medical Staff"],
                _("{0} health incident — {1}").format(self.severity, self.child),
                self.description or "",
                self.doctype,
                self.name,
            )
