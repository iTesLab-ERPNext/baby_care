import frappe
from frappe import _
from frappe.model.document import Document

from baby_care.baby_care_management.utils import parent_access


class ParentProfile(Document):
    def validate(self):
        self.first_name = (self.first_name or "").strip()
        self.last_name = (self.last_name or "").strip()
        self.full_name = " ".join(x for x in (self.first_name, self.last_name) if x)
        self.email = (self.email or "").strip().lower() or None
        if self.email:
            frappe.utils.validate_email_address(self.email, throw=True)
        parent_access.profile_validate(self)

    def on_update(self):
        parent_access.profile_on_update(self)

    def on_trash(self):
        if frappe.get_all("Child Parent Link", filters={"parent_profile": self.name, "parenttype": "Child"}, limit=1):
            frappe.throw(_("{0} is linked to a child. Remove the parent from the child first.").format(self.full_name))
        parent_access.profile_on_trash(self)

    @frappe.whitelist()
    def get_summary(self):
        from baby_care.baby_care_management.utils.billing import get_parent_statement

        return get_parent_statement(self.name)
