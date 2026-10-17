import frappe
from frappe import _
from frappe.model.document import Document


class MealPlan(Document):
    def validate(self):
        seen = set()
        for row in self.items or []:
            key = (row.day_of_week, row.meal_category)
            if key in seen:
                frappe.throw(_("{0} / {1} appears twice in the menu.").format(row.day_of_week, row.meal_category))
            seen.add(key)

    def allergens(self):
        found = set()
        for row in self.items or []:
            for a in (row.allergens or "").replace(";", ",").split(","):
                if a.strip():
                    found.add(a.strip().lower())
        return found
