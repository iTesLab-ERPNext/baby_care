"""Tests for Child DocType."""
import unittest
import frappe
from frappe.utils import today


class TestChild(unittest.TestCase):
    def setUp(self):
        # Ensure a parent customer exists
        if not frappe.db.exists("Customer", "Test Parent"):
            c = frappe.new_doc("Customer")
            c.customer_name = "Test Parent"
            c.customer_group = "Individual"
            c.territory = "All Territories"
            c.insert(ignore_permissions=True)

    def _make_child(self, first="Test", last="Child"):
        child = frappe.new_doc("Child")
        child.first_name = first
        child.last_name = last
        child.date_of_birth = "2021-06-01"
        child.gender = "Male"
        child.enrollment_status = "Active"
        child.registration_date = today()
        child.append("parents", {
            "parent_customer": "Test Parent",
            "relationship": "Father",
            "is_primary": 1,
        })
        return child

    def test_full_name_set_on_validate(self):
        child = self._make_child("John", "Doe")
        child.insert(ignore_permissions=True)
        self.assertEqual(child.full_name, "John Doe")
        frappe.delete_doc("Child", child.name, force=True)

    def test_requires_parent(self):
        child = self._make_child()
        child.parents = []
        with self.assertRaises(frappe.ValidationError):
            child.insert(ignore_permissions=True)

    def test_age_display_set(self):
        child = self._make_child()
        child.insert(ignore_permissions=True)
        self.assertTrue(child.age_display)
        frappe.delete_doc("Child", child.name, force=True)


class TestSubscriptionPlan(unittest.TestCase):
    def test_negative_price_rejected(self):
        plan = frappe.new_doc("Subscription Plan")
        plan.plan_name = "_test_plan_bad"
        plan.billing_frequency = "Monthly"
        plan.base_price = -10
        with self.assertRaises(frappe.ValidationError):
            plan.insert(ignore_permissions=True)


class TestAgeGroup(unittest.TestCase):
    def test_min_less_than_max(self):
        ag = frappe.new_doc("Age Group")
        ag.group_name = "_test_age_bad"
        ag.min_age_months = 12
        ag.max_age_months = 6
        with self.assertRaises(frappe.ValidationError):
            ag.insert(ignore_permissions=True)


if __name__ == "__main__":
    unittest.main()
