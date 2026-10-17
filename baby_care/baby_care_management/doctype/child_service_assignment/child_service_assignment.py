import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class ChildServiceAssignment(Document):
    def validate(self):
        if self.start_date and self.end_date and getdate(self.end_date) < getdate(self.start_date):
            frappe.throw(_("End date cannot be before start date."))
        svc = frappe.get_doc("Nursery Service", self.service)
        if self.status == "Active" and not svc.is_available_on(self.start_date or frappe.utils.today()):
            frappe.throw(_("Service {0} is not available for this period.").format(self.service))
        if svc.availability == "Selected Age Groups" or svc.availability == "Selected Classes":
            frappe.msgprint(_("Check eligibility: {0}").format(svc.eligibility_notes or svc.availability), alert=True)
        dup = frappe.db.get_value(
            "Child Service Assignment",
            {"child": self.child, "service": self.service, "status": "Active", "name": ("!=", self.name)},
            "name",
        )
        if self.status == "Active" and dup:
            frappe.throw(_("{0} is already assigned to {1} ({2}).").format(self.service, self.child, dup))
