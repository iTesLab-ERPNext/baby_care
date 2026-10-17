import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, validate_email_address


class TeacherProfile(Document):
    def validate(self):
        if self.email:
            validate_email_address(self.email, throw=True)
        if self.start_date and self.end_date and getdate(self.end_date) < getdate(self.start_date):
            frappe.throw(_("End date cannot be before start date."))
        if self.user_account:
            other = frappe.db.get_value(
                "Teacher Profile", {"user_account": self.user_account, "name": ("!=", self.name)}, "name"
            )
            if other:
                frappe.throw(_("User {0} is already linked to teacher {1}.").format(self.user_account, other))

    def on_update(self):
        self._grant_teacher_role()
        if self.employment_status != "Active" and self.has_value_changed("employment_status"):
            count = frappe.db.count("Child", {"assigned_teacher": self.name, "enrollment_status": "Active"})
            if count:
                frappe.msgprint(
                    _("{0} active children are still assigned to this teacher. Reassign them from the Child list.").format(count),
                    indicator="orange",
                    alert=True,
                )

    def _grant_teacher_role(self):
        """A linked user needs the Nursery Teacher role to see assigned children."""
        if not self.user_account or self.user_account in ("Administrator", "Guest"):
            return
        if "Nursery Teacher" in frappe.get_roles(self.user_account):
            return
        user = frappe.get_doc("User", self.user_account)
        user.add_roles("Nursery Teacher")

    @frappe.whitelist()
    def get_assigned_children(self):
        from baby_care.baby_care_management.utils.permissions import get_teacher_classes

        classes = get_teacher_classes(self.name)
        or_filters = {"assigned_teacher": self.name}
        if classes:
            or_filters["nursery_class"] = ("in", classes)
        return frappe.get_list(
            "Child",
            or_filters=or_filters,
            filters={"enrollment_status": ("in", ["Active", "Pending"])},
            fields=["name", "full_name", "nursery_class", "age_display", "has_allergies"],
            order_by="full_name asc",
        )
