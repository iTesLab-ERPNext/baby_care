import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class NurseryClass(Document):
    def validate(self):
        self._dedupe_children()
        self._validate_teachers()
        self.current_enrollment = len([c for c in (self.children or []) if c.enrollment_status == "Active"])
        self._check_capacity()

    def on_update(self):
        if self.flags.from_child_sync:
            return
        # Rows added or changed directly on the class become the child's class.
        for row in self.children or []:
            if row.enrollment_status == "Active":
                current = frappe.db.get_value("Child", row.child, "nursery_class")
                if current != self.name:
                    frappe.db.set_value("Child", row.child, "nursery_class", self.name)

    def _dedupe_children(self):
        seen = set()
        for row in self.children or []:
            if row.child in seen:
                frappe.throw(_("Child {0} is listed twice in this class.").format(row.child))
            seen.add(row.child)

    def _validate_teachers(self):
        primaries = 0
        for row in self.teachers or []:
            status = frappe.db.get_value("Teacher Profile", row.teacher, "employment_status")
            if status != "Active":
                frappe.throw(_("Teacher {0} is not active.").format(row.teacher))
            primaries += cint(row.is_primary)
        if primaries > 1:
            frappe.throw(_("Only one primary teacher per class."))

    def _check_capacity(self):
        if not cint(frappe.db.get_single_value("Nursery Settings", "enforce_class_capacity")):
            return
        if cint(self.capacity) and self.current_enrollment > cint(self.capacity):
            frappe.throw(
                _("Class {0} is over capacity ({1}/{2}).").format(self.class_name, self.current_enrollment, self.capacity)
            )
