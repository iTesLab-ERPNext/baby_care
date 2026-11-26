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


class TestSchemaAndDesk(FrappeTestCase):
    """Regression guards for issues that only showed up in the browser."""

    def test_table_fields_are_valid(self):
        for dt in frappe.get_all("DocType", {"module": "Baby Care Management", "istable": 0}, pluck="name"):
            for df in frappe.get_meta(dt).fields:
                if df.fieldtype not in ("Table", "Table MultiSelect"):
                    continue
                child = frappe.get_meta(df.options)
                self.assertTrue(child.istable, f"{dt}.{df.fieldname} must point to a child table")
                if df.fieldtype == "Table MultiSelect":
                    links = [f for f in child.fields if f.fieldtype == "Link"]
                    self.assertEqual(len(links), 1, f"{dt}.{df.fieldname}: Table MultiSelect needs exactly one Link column")
                    self.assertEqual(len(child.fields), 1, f"{dt}.{df.fieldname}: use Table for multi-column rows (grid needed by set_query)")

    def test_count_widgets_have_no_currency(self):
        from baby_care.baby_care_management.setup.desk import MONEY_CARDS, MONEY_CHARTS, NUMBER_CARDS, _charts

        for label, _m, _c in NUMBER_CARDS:
            cur = frappe.db.get_value("Number Card", label, "currency")
            self.assertEqual(bool(cur), label in MONEY_CARDS, label)
        for chart in _charts():
            cur = frappe.db.get_value("Dashboard Chart", chart["chart_name"], "currency")
            self.assertEqual(bool(cur), chart["chart_name"] in MONEY_CHARTS, chart["chart_name"])


class TestNavbarMenu(BabyCareTestBase):
    def _routes(self, user):
        from baby_care.baby_care_management.api.navigation import get_menu

        menu = get_menu(user)
        return menu, [i["route"] for s in (menu or {}).get("sections", []) for i in s["items"]]

    def test_admin_menu_matches_workspace(self):
        from baby_care.baby_care_management.setup.desk import SECTIONS

        menu, routes = self._routes("Administrator")
        self.assertEqual([s["label"] for s in menu["sections"]], [t for t, _ in SECTIONS])
        self.assertIn("/app/child", routes)
        self.assertIn("/app/query-report/Revenue Report", routes)
        self.assertIn("/app/dashboard-view/Baby Care Dashboard", routes)

    def test_menu_follows_permissions(self):
        teacher = _user("ut-nav-teacher@bc.test", ["Nursery Teacher"])
        _menu, routes = self._routes(teacher)
        self.assertIn("/app/child-attendance", routes)
        for hidden in ("/app/sales-invoice", "/app/medical-record", "/app/payment-entry", "/app/permission-manager"):
            self.assertNotIn(hidden, routes)
        outsider = _user("ut-nav-none@bc.test", ["Blogger"])
        self.assertIsNone(self._routes(outsider)[0])


class TestParentAPI(BabyCareTestBase):
    """Parent API called as a real parent user (portal user of one family)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from baby_care.baby_care_management.api.parents import create_parent_user

        frappe.set_user("Administrator")
        cls.sara = frappe.db.get_value("Customer", {"customer_name": ("like", "Sara%[TEST]")}, "name")
        cls.parent = create_parent_user(cls.sara, "ut-parent@bc.test", send_welcome_email=0)["user"]
        cls.outsider = _user("ut-outsider@bc.test", ["Nursery Teacher"])

    def setUp(self):
        frappe.set_user(self.parent)

    def test_parent_role_and_link(self):
        frappe.set_user("Administrator")
        self.assertIn("Nursery Parent", frappe.get_roles(self.parent))
        self.assertEqual(frappe.db.get_value("User", self.parent, "user_type"), "Website User")
        self.assertIn(self.parent, frappe.get_all("Portal User", {"parent": self.sara}, pluck="user"))

    def test_children_scoped_to_family(self):
        from baby_care.api import v1

        names = {c.full_name.split()[0] for c in v1.children()}
        self.assertEqual(names, {"Adam", "Lina"})

    def test_other_family_is_not_found(self):
        from baby_care.api import v1

        for endpoint in (v1.child, v1.child_tracking, v1.child_attendance, v1.child_meals, v1.child_incidents, v1.child_documents):
            with self.assertRaises(frappe.DoesNotExistError):
                endpoint(child=self.kids["Omar"])
        other_invoice = frappe.get_all("Sales Invoice", {"customer": ("!=", self.sara), "docstatus": 1}, pluck="name", limit=1)
        if other_invoice:
            with self.assertRaises(frappe.DoesNotExistError):
                v1.invoice(other_invoice[0])

    def test_tracking_and_billing(self):
        from baby_care.api import v1

        t = v1.child_tracking(child=self.kids["Adam"])
        self.assertIn("attendance_30_days", t)
        self.assertTrue(t["meals"] is not None)
        inv = v1.invoices()
        self.assertEqual(len(inv), 2)
        bal = v1.balance()
        self.assertAlmostEqual(bal["invoiced"], sum(i.grand_total for i in inv), places=2)
        self.assertEqual(len(v1.subscriptions()), 2)

    def test_validation(self):
        from baby_care.api import v1

        with self.assertRaises(frappe.ValidationError):
            v1.invoices(status="bogus")
        with self.assertRaises(frappe.ValidationError):
            v1.child_attendance(child=self.kids["Adam"], from_date="not-a-date")

    def test_unlinked_user_refused(self):
        from baby_care.api import v1

        frappe.set_user(self.outsider)
        with self.assertRaises(frappe.PermissionError):
            v1.children()

    def test_openapi_matches_endpoints(self):
        from baby_care.api import spec, v1

        doc = spec.openapi()
        self.assertEqual(len(doc["paths"]), len(spec.ENDPOINTS))
        for name, *_ in spec.ENDPOINTS:
            self.assertTrue(callable(getattr(v1, name, None)), f"documented endpoint {name} is not implemented")


class TestClearAfterPayment(FrappeTestCase):
    """Clearing demo data must work after a user recorded a payment on a demo invoice."""

    def test_clear_with_paid_demo_invoice(self):
        from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

        frappe.set_user("Administrator")
        if not seed._registry():
            seed.install_test_data()
        si = next((n for dt, n in seed._registry() if dt == "Sales Invoice" and frappe.db.get_value("Sales Invoice", n, "outstanding_amount")), None)
        if not si:
            self.skipTest("no unpaid demo invoice")
        pe = get_payment_entry("Sales Invoice", si)
        pe.reference_no, pe.reference_date = "UT", today()
        pe.insert(ignore_permissions=True)
        pe.submit()
        seed.clear_test_data()
        self.assertFalse(frappe.db.exists("Sales Invoice", si))
        self.assertFalse(frappe.db.exists("Payment Entry", pe.name))
        self.assertEqual(frappe.db.count("Customer", {"customer_name": ("like", "%[TEST]")}), 0)


class TestParentApp(BabyCareTestBase):
    """Parent App credentials (Customer form) and the mobile endpoints."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")
        cls.login = "ut-app-karim@bc.test"
        cls.karim = frappe.get_doc({"doctype": "Customer", "customer_name": "UT App Parent", "customer_type": "Individual",
                                    "customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}),
                                    "territory": "All Territories"}).insert(ignore_permissions=True).name

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        cls._reset(cls.karim)
        frappe.delete_doc("Customer", cls.karim, force=True, ignore_permissions=True)
        frappe.db.commit()
        super().tearDownClass()

    @staticmethod
    def _reset(customer):
        main = frappe.db.get_value("Customer", customer, "bc_parent_user")
        for u in {"ut-app-karim@bc.test", "ut-app-karim2@bc.test", "ut-app-extra@bc.test"}:
            frappe.db.delete("Portal User", {"parent": customer, "user": u})
            if frappe.db.exists("User", u) and u != main:
                frappe.delete_doc("User", u, force=True, ignore_permissions=True)
        if main in {"ut-app-karim@bc.test", "ut-app-karim2@bc.test"}:
            frappe.db.delete("Portal User", {"parent": customer, "user": main})
            frappe.delete_doc("User", main, force=True, ignore_permissions=True)
            frappe.db.set_value("Customer", customer, {"bc_parent_app_access": 0, "bc_parent_login": None, "bc_parent_user": None})

    def _enable(self, password="Cedar#Lake58", login=None):
        frappe.set_user("Administrator")
        c = frappe.get_doc("Customer", self.karim)
        c.bc_parent_app_access = 1
        c.bc_parent_login = login or self.login
        c.bc_parent_password = password
        c.save()
        return frappe.get_doc("Customer", self.karim)

    def test_password_set_from_customer_form(self):
        from frappe.utils.password import check_password

        c = self._enable()
        self.assertEqual(c.bc_parent_user, self.login)
        self.assertEqual(check_password(self.login, "Cedar#Lake58"), self.login)
        self.assertIn("Nursery Parent", frappe.get_roles(self.login))
        self.assertEqual(frappe.db.get_value("User", self.login, "user_type"), "Website User")
        self.assertFalse(c.get("bc_parent_password"))
        self.assertFalse(frappe.db.exists("__Auth", {"doctype": "Customer", "name": self.karim, "fieldname": "bc_parent_password"}))

    def test_weak_password_refused(self):
        frappe.set_user("Administrator")
        c = frappe.get_doc("Customer", self.karim)
        c.bc_parent_app_access, c.bc_parent_login, c.bc_parent_password = 1, self.login, "short"
        with self.assertRaises(frappe.ValidationError):
            c.save()

    def test_staff_account_refused(self):
        frappe.set_user("Administrator")
        staff = _user("ut-app-staff@bc.test", ["Nursery Teacher"])
        frappe.db.set_value("User", staff, "user_type", "System User")
        c = frappe.get_doc("Customer", self.karim)
        c.bc_parent_app_access, c.bc_parent_login = 1, staff
        with self.assertRaises(frappe.ValidationError):
            c.save()

    def test_change_password_rotates_token(self):
        from baby_care.api import v1

        self._enable()
        old = v1._api_token(self.login)
        self.assertEqual(old, v1._api_token(self.login))  # stable between logins
        frappe.set_user(self.login)
        with self.assertRaises(frappe.ValidationError):
            v1.change_password("wrong-one", "Maple#Road31")
        new = v1.change_password("Cedar#Lake58", "Maple#Road31")["token"]
        self.assertNotEqual(old.split(":")[1], new.split(":")[1])
        self.assertEqual(old.split(":")[0], new.split(":")[0])

    def test_register_device_and_feed(self):
        from baby_care.api import v1

        self._enable()
        frappe.set_user(self.login)
        with self.assertRaises(frappe.ValidationError):
            v1.register_device("not-a-token")
        v1.register_device("ExponentPushToken[ut-123]", "android", "Pixel")
        self.assertTrue(frappe.db.exists("Parent App Device", {"user": self.login, "push_token": "ExponentPushToken[ut-123]"}))
        feed = v1.notifications()
        self.assertFalse([f for f in feed if f.get("child")])  # this family has no children
        v1.app_logout(push_token="ExponentPushToken[ut-123]")
        self.assertFalse(frappe.db.exists("Parent App Device", {"user": self.login}))

    def test_login_change_renames_user(self):
        c = self._enable()
        c = self._enable(password=None, login="ut-app-karim2@bc.test")
        self.assertEqual(c.bc_parent_user, "ut-app-karim2@bc.test")
        self.assertFalse(frappe.db.exists("User", self.login))
        links = frappe.get_all("Portal User", {"parent": self.karim}, pluck="user")
        self.assertIn("ut-app-karim2@bc.test", links)
        self.assertNotIn(self.login, links)
        self._enable(password=None, login=self.login)

    def test_disable_signs_out(self):
        from baby_care.api import v1
        from baby_care.baby_care_management.api.parents import create_parent_user

        self._enable()
        extra = create_parent_user(self.karim, "ut-app-extra@bc.test", send_welcome_email=0)["user"]
        self.assertEqual(frappe.db.get_value("Customer", self.karim, "bc_parent_user"), self.login)  # main login kept
        token = v1._api_token(self.login)
        c = frappe.get_doc("Customer", self.karim)
        c.bc_parent_app_access = 0
        c.save()
        self.assertFalse(frappe.db.get_value("User", self.login, "enabled"))
        self.assertFalse(frappe.db.get_value("User", extra, "enabled"))
        self.assertNotEqual(token, v1._api_token(self.login))
        self._enable()
        self.assertTrue(frappe.db.get_value("User", self.login, "enabled"))

    def test_plain_customer_untouched(self):
        frappe.set_user("Administrator")
        c = frappe.get_doc({"doctype": "Customer", "customer_name": "UT Plain Customer", "customer_type": "Company",
                            "customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}),
                            "territory": "All Territories", "email_id": "ut-plain@bc.test"}).insert(ignore_permissions=True)
        c.save()
        self.assertFalse(frappe.db.exists("User", "ut-plain@bc.test"))
        self.assertFalse(frappe.get_all("Portal User", {"parent": c.name}))
        frappe.delete_doc("Customer", c.name, force=True)
