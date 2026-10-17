"""
Integration tests for Baby Care Management.

Run on a site with ERPNext set up (company + chart of accounts):

    bench --site <site> set-config allow_tests true
    bench --site <site> run-tests --module baby_care.tests.test_baby_care

The suite installs the tracked demo data set once (Data Management →
Install Test Data), runs against those real records and removes them again.
"""
import json

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_months, flt, today

from baby_care.baby_care_management.api import seed


def _user(email, roles):
    if not frappe.db.exists("User", email):
        frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0}).insert(ignore_permissions=True)
    user = frappe.get_doc("User", email)
    user.roles = []
    user.save(ignore_permissions=True)
    user.add_roles(*roles)
    return email


class BabyCareTestBase(FrappeTestCase):
    installed_here = False

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")
        if not seed._registry():
            seed.install_test_data()
            BabyCareTestBase.installed_here = True
        cls.kids = {c.first_name: c.name for c in frappe.get_all("Child", {"full_name": ("like", "%[TEST]%")}, ["name", "first_name"])}

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        if BabyCareTestBase.installed_here:
            seed.clear_test_data()
            BabyCareTestBase.installed_here = False
        super().tearDownClass()

    def tearDown(self):
        frappe.set_user("Administrator")


class TestWorkspace(BabyCareTestBase):
    def test_workspace_links_resolve(self):
        ws = frappe.get_doc("Workspace", "Baby Care Management")
        cards = [l.label for l in ws.links if l.type == "Card Break"]
        for title in ("Dashboard", "Parents & Children", "Subscriptions & Billing", "Health & Documents", "Services & Activities",
                      "Staff & Attendance", "Reports", "Configuration", "Data Management"):
            self.assertIn(title, cards)
        for link in ws.links:
            if link.type == "Card Break":
                continue
            self.assertIn(link.link_type, ("DocType", "Report", "Page"), link.label)
            if link.link_type == "DocType":
                self.assertFalse(frappe.db.get_value("DocType", link.link_to, "istable"), link.link_to)
            else:
                self.assertTrue(frappe.db.exists(link.link_type, link.link_to), link.link_to)
        content = json.loads(ws.content)
        names = {b["data"].get("card_name") for b in content if b["type"] == "card"}
        self.assertEqual(names, set(cards))

    def test_desk_renders_cards(self):
        from frappe.desk.desktop import get_desktop_page

        page = get_desktop_page(json.dumps({"name": "Baby Care Management", "title": "Baby Care Management", "public": 1}))
        self.assertGreaterEqual(len(page["cards"]["items"]), 9)
        self.assertTrue(all(c["links"] for c in page["cards"]["items"]))

    def test_number_cards_compute(self):
        from baby_care.baby_care_management.setup.desk import NUMBER_CARDS

        for label, _method, _color in NUMBER_CARDS:
            card = frappe.get_doc("Number Card", label)
            self.assertIn("value", frappe.get_attr(card.method)())
        from baby_care.baby_care_management.api.dashboard import enrolled_children

        self.assertGreaterEqual(enrolled_children()["value"], 5)


class TestBilling(BabyCareTestBase):
    def test_invoice_amounts_and_family_discount(self):
        lina_sub = frappe.db.get_value("Child Subscription", {"child": self.kids["Lina"], "docstatus": 1}, ["name", "discount_percent", "final_amount"], as_dict=True)
        self.assertEqual(flt(lina_sub.discount_percent), 10, "second child of the same parent gets the family discount")
        si = frappe.get_doc("Sales Invoice", {"baby_care_subscription": lina_sub.name})
        # quarterly plan 990 + 3 months of transport at 40, minus 10%
        self.assertAlmostEqual(flt(si.grand_total), (990 + 120) * 0.9, places=2)
        self.assertEqual(si.baby_care_child, self.kids["Lina"])

    def test_duplicate_period_is_blocked(self):
        from baby_care.baby_care_management.utils.billing import create_subscription_invoice

        sub = frappe.get_doc("Child Subscription", {"child": self.kids["Adam"], "docstatus": 1})
        nxt = sub.next_billing_date
        frappe.db.set_value("Child Subscription", sub.name, "next_billing_date", sub.start_date)
        with self.assertRaises(frappe.ValidationError):
            create_subscription_invoice(sub.name)
        frappe.db.set_value("Child Subscription", sub.name, "next_billing_date", nxt)

    def test_payment_updates_subscription_invoice_status(self):
        from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

        sub = frappe.get_doc("Child Subscription", {"child": self.kids["Omar"], "docstatus": 1})
        si = frappe.get_doc("Sales Invoice", {"baby_care_subscription": sub.name, "docstatus": 1})
        pe = get_payment_entry("Sales Invoice", si.name)
        pe.reference_no, pe.reference_date = "TEST", today()
        pe.insert(ignore_permissions=True)
        pe.submit()
        status = frappe.db.get_value("Child Subscription Invoice", {"sales_invoice": si.name}, "status")
        self.assertEqual(status, "Paid")
        pe.cancel()
        self.assertNotEqual(frappe.db.get_value("Child Subscription Invoice", {"sales_invoice": si.name}, "status"), "Paid")


class TestSubscriptionRules(BabyCareTestBase):
    def test_overlapping_subscription_rejected(self):
        child = frappe.get_doc("Child", self.kids["Adam"])
        dup = frappe.get_doc({"doctype": "Child Subscription", "child": child.name, "parent_customer": child.parents[0].parent_customer,
                              "subscription_plan": "Monthly Full Day", "start_date": today()})
        with self.assertRaises(frappe.ValidationError):
            dup.insert()

    def test_parent_must_be_linked(self):
        stranger = frappe.db.get_value("Customer", {"customer_name": ("like", "Karim%[TEST]")}, "name")
        sub = frappe.get_doc({"doctype": "Child Subscription", "child": self.kids["Adam"], "parent_customer": stranger,
                              "subscription_plan": "Monthly Full Day", "start_date": add_months(today(), 24)})
        with self.assertRaises(frappe.ValidationError):
            sub.insert()

    def test_suspend_resume_renew(self):
        sub = frappe.get_doc("Child Subscription", {"child": self.kids["Rayan"], "docstatus": 1})
        end = sub.end_date
        sub.suspend("holiday")
        self.assertEqual(frappe.db.get_value("Child", sub.child, "subscription_status"), "Suspended")
        sub.reload(); sub.resume()
        sub.reload(); new_end = sub.renew()
        self.assertGreater(str(new_end), str(end))
        self.assertEqual(frappe.db.get_value("Child Subscription", sub.name, "status"), "Active")


class TestBusinessRules(BabyCareTestBase):
    def test_child_requires_parent(self):
        child = frappe.get_doc({"doctype": "Child", "first_name": "No", "last_name": "Parent", "date_of_birth": "2023-01-01", "gender": "Male"})
        with self.assertRaises(frappe.ValidationError):
            child.insert()

    def test_inactive_teacher_cannot_be_assigned(self):
        t = frappe.get_doc({"doctype": "Teacher Profile", "full_name": "Inactive Teacher [UT]", "employment_status": "Inactive"}).insert()
        child = frappe.get_doc("Child", self.kids["Adam"])
        child.assigned_teacher = t.name
        with self.assertRaises(frappe.ValidationError):
            child.save()
        frappe.delete_doc("Teacher Profile", t.name, force=True)

    def test_class_capacity(self):
        cls = frappe.get_doc("Nursery Class", {"class_name": "Butterflies [TEST]"})
        cls.capacity = 1
        with self.assertRaises(frappe.ValidationError):
            cls.save()

    def test_meal_plan_respects_allergy(self):
        plan = frappe.get_doc({"doctype": "Child Meal Plan", "child": self.kids["Omar"], "meal_plan": "Standard Week", "start_date": today(), "is_active": 1})
        with self.assertRaises(frappe.ValidationError):
            plan.insert()

    def test_pickup_must_be_authorized(self):
        att = frappe.get_doc({"doctype": "Child Attendance", "child": self.kids["Adam"], "attendance_date": add_days(today(), -60),
                              "status": "Present", "check_in_time": "08:00:00", "check_out_time": "16:00:00", "pickup_person": "Unknown Person"})
        with self.assertRaises(frappe.ValidationError):
            att.insert()
        att.pickup_person = "Grandma [TEST]"
        att.insert()
        att.delete()

    def test_one_attendance_per_day(self):
        existing = frappe.get_all("Child Attendance", {"child": self.kids["Adam"]}, ["attendance_date"], limit=1)[0]
        dup = frappe.get_doc({"doctype": "Child Attendance", "child": self.kids["Adam"], "attendance_date": existing.attendance_date, "status": "Present"})
        with self.assertRaises(frappe.ValidationError):
            dup.insert()

    def test_absent_clears_times(self):
        att = frappe.get_doc({"doctype": "Child Attendance", "child": self.kids["Lina"], "attendance_date": add_days(today(), -61), "status": "Absent", "absence_reason": "Sick"}).insert()
        self.assertFalse(att.check_in_time)
        self.assertFalse(att.check_out_time)
        att.delete()


class TestScheduler(BabyCareTestBase):
    def test_daily_tasks_and_deduplication(self):
        from baby_care.baby_care_management.utils import scheduler

        scheduler.daily_tasks()
        first = frappe.db.count("Notification Log", {"subject": ("like", "Missing documents%")})
        scheduler.daily_tasks()
        self.assertEqual(first, frappe.db.count("Notification Log", {"subject": ("like", "Missing documents%")}))

    def test_expired_subscription_is_closed(self):
        sub = frappe.get_doc("Child Subscription", {"child": self.kids["Yasmine"], "docstatus": 1})
        end = sub.end_date
        frappe.db.set_value("Child Subscription", sub.name, "end_date", add_days(today(), -1))
        from baby_care.baby_care_management.utils.scheduler import update_subscription_lifecycle

        update_subscription_lifecycle()
        self.assertEqual(frappe.db.get_value("Child Subscription", sub.name, "status"), "Expired")
        frappe.db.set_value("Child Subscription", sub.name, {"end_date": end, "status": "Active"})


class TestPermissions(BabyCareTestBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.teacher = _user("ut-teacher@bc.test", ["Nursery Teacher"])
        cls.accountant = _user("ut-acc@bc.test", ["Nursery Accountant", "Accounts User"])
        cls.medical = _user("ut-med@bc.test", ["Nursery Medical Staff"])
        cls.admin = _user("ut-admin@bc.test", ["Nursery Administrator"])
        leila = frappe.db.get_value("Teacher Profile", {"full_name": ("like", "Leila%[TEST]")}, "name")
        frappe.db.set_value("Teacher Profile", leila, "user_account", cls.teacher)

    def test_admin_sees_everything(self):
        frappe.set_user(self.admin)
        self.assertTrue(set(self.kids.values()) <= set(frappe.get_list("Child", pluck="name", limit_page_length=0)))
        self.assertEqual(len(frappe.get_list("Medical Record", filters={"child": ("in", list(self.kids.values()))}, pluck="name")), 5)

    def test_teacher_restricted_to_assigned_children(self):
        frappe.set_user(self.teacher)
        visible = set(frappe.get_list("Child", filters={"name": ("in", list(self.kids.values()))}, pluck="name"))
        self.assertEqual(visible, {self.kids["Adam"], self.kids["Omar"]})
        self.assertFalse(frappe.has_permission("Child", "read", doc=self.kids["Lina"]))
        self.assertFalse(frappe.has_permission("Medical Record", "read"))
        self.assertFalse(frappe.has_permission("Sales Invoice", "read"))

    def test_accountant_no_medical(self):
        frappe.set_user(self.accountant)
        self.assertTrue(frappe.has_permission("Child Subscription", "read"))
        self.assertFalse(frappe.has_permission("Medical Record", "read"))

    def test_medical_no_finance(self):
        frappe.set_user(self.medical)
        self.assertTrue(frappe.has_permission("Medical Record", "read"))
        self.assertFalse(frappe.has_permission("Sales Invoice", "read"))
        self.assertFalse(frappe.has_permission("Child Subscription", "read"))
