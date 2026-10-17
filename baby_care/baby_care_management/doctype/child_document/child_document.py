import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today


class ChildDocument(Document):
    def validate(self):
        if self.document_for == "Parent":
            self.child = None
        else:
            self.parent_customer = None
        cfg = frappe.db.get_value("Document Type Config", self.document_type, ["applies_to", "has_expiry"], as_dict=True)
        if cfg and cfg.applies_to not in ("Both", self.document_for):
            frappe.throw(_("Document type {0} applies to {1} only.").format(self.document_type, cfg.applies_to))
        if self.issue_date and self.expiry_date and getdate(self.expiry_date) < getdate(self.issue_date):
            frappe.throw(_("Expiry date cannot be before the issue date."))
        if cfg and cfg.has_expiry and not self.expiry_date and self.status == "Valid":
            frappe.msgprint(_("This document type normally has an expiry date."), alert=True)
        self.is_private = 1
        self._set_status()

    def _set_status(self):
        if self.status == "Revoked":
            return
        if not self.attached_file:
            self.status = "Missing"
        elif self.expiry_date and getdate(self.expiry_date) < getdate(today()):
            self.status = "Expired"
        else:
            self.status = "Valid"


def get_missing_mandatory_documents(child=None):
    """[(child, document_type)] for active children missing a valid mandatory document."""
    mandatory = frappe.get_all("Document Type Config", filters={"is_mandatory": 1, "is_active": 1, "applies_to": ("in", ["Child", "Both"])}, pluck="name")
    if not mandatory:
        return []
    filters = {"enrollment_status": "Active"}
    if child:
        filters["name"] = child
    out = []
    for c in frappe.get_all("Child", filters=filters, pluck="name"):
        have = set(frappe.get_all("Child Document", filters={"child": c, "status": "Valid"}, pluck="document_type"))
        out.extend((c, d) for d in mandatory if d not in have)
    return out
