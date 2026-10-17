import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class ChildMealPlan(Document):
    def validate(self):
        if self.start_date and self.end_date and getdate(self.end_date) < getdate(self.start_date):
            frappe.throw(_("End date cannot be before start date."))
        self._check_allergens()
        self._single_active_plan()

    def _check_allergens(self):
        """Child-specific restrictions override the meal plan: block incompatible plans."""
        from baby_care.baby_care_management.doctype.medical_record.medical_record import get_child_allergens

        child_allergens = set(get_child_allergens(self.child))
        if not child_allergens:
            return
        plan = frappe.get_doc("Meal Plan", self.meal_plan)
        conflicts = sorted(a for a in plan.allergens() if any(a in c or c in a for c in child_allergens))
        if conflicts:
            frappe.throw(
                _("Meal plan {0} contains {1}, which {2} is allergic to. Choose another plan or adjust the menu.").format(
                    self.meal_plan, ", ".join(conflicts), self.child
                ),
                title=_("Dietary restriction"),
            )

    def _single_active_plan(self):
        if not self.is_active:
            return
        other = frappe.db.get_value(
            "Child Meal Plan", {"child": self.child, "is_active": 1, "name": ("!=", self.name)}, "name"
        )
        if other:
            frappe.db.set_value("Child Meal Plan", other, "is_active", 0)
            frappe.msgprint(_("Previous meal plan {0} was deactivated.").format(other), alert=True)
