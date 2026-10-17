import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today

SEVERE = ("Severe", "Life-Threatening")


class MedicalRecord(Document):
    def validate(self):
        self._one_record_per_child()
        for v in self.vaccinations or []:
            if v.date_given and getdate(v.date_given) > getdate(today()):
                frappe.throw(_("Vaccination {0}: date given cannot be in the future.").format(v.vaccine_name))
        for m in self.current_medications or []:
            if m.start_date and m.end_date and getdate(m.end_date) < getdate(m.start_date):
                frappe.throw(_("Medication {0}: end date is before start date.").format(m.medication_name))

    def on_update(self):
        self._update_child_flags()
        severe = [a.allergen for a in self.allergies or [] if a.severity in SEVERE]
        if severe and self.has_value_changed("modified"):
            frappe.msgprint(_("Severe allergies recorded: {0}").format(", ".join(severe)), indicator="red", alert=True)

    def on_trash(self):
        frappe.db.set_value("Child", self.child, {"has_allergies": 0, "has_chronic_condition": 0}, update_modified=False)

    def _one_record_per_child(self):
        other = frappe.db.get_value("Medical Record", {"child": self.child, "name": ("!=", self.name)}, "name")
        if other:
            frappe.throw(_("Child {0} already has medical record {1}. Update that record instead — its history is tracked.").format(self.child, other))

    def _update_child_flags(self):
        frappe.db.set_value(
            "Child",
            self.child,
            {"has_allergies": 1 if self.allergies else 0, "has_chronic_condition": 1 if self.chronic_conditions else 0},
            update_modified=False,
        )


def get_child_allergens(child):
    """Allergen names for a child, read without user permissions (used for safety checks)."""
    rec = frappe.db.get_value("Medical Record", {"child": child}, "name")
    if not rec:
        return []
    return [a.lower().strip() for a in frappe.get_all("Child Allergy", filters={"parent": rec, "parenttype": "Medical Record"}, pluck="allergen") if a]
