# Baby Care Management

Nursery, daycare, kindergarten and baby-care centre management for **ERPNext v15 and v16**.
Parents are ERPNext **Customers**, billing uses ERPNext **Sales Invoice** and **Payment Entry**,
and every rule that varies between facilities is configuration, not code.

Version 1.1.1 is tested end-to-end on Frappe v15 + ERPNext v15: fresh install, upgrade from
1.0, uninstall, 24 automated tests, a 44-check role-permission audit and a browser test that opens every form for every role.

---

## Install

```bash
cd ~/frappe-bench
bench get-app https://github.com/iTesLab-ERPNext/baby_care     # or copy the folder into apps/
./env/bin/pip install -e apps/baby_care                         # only if get-app did not install it
bench --site <site> install-app baby_care
bench --site <site> migrate
bench build --app baby_care
bench --site <site> clear-cache
```

ERPNext's setup wizard must be completed first (a Company and chart of accounts are needed for invoicing).

### Upgrading from 1.0

Replace the app folder and run `bench --site <site> migrate`. The old workspace is replaced, existing
children keep their names (new children are numbered `CHILD-00001`), and no data is removed.

### First steps

1. **Baby Care Management → Data Management → Install Seed Data**: services, subscription plans,
   meal plans and a transport route you can edit.
2. Optional: **Install Test Data** loads tagged demo parents, children, teachers, attendance,
   subscriptions and invoices. **Clear Test Data** removes exactly those records.
3. **Configuration → Application Settings**: set company, income account, cost centre, invoice due
   days, family discount, notification windows and the operational switches.

---

## Workspace (`/app/baby-care-management`)

The top of the page shows 8 live number cards and 4 charts, followed by 8 shortcuts and 9 cards:

| Section | Links |
|---|---|
| Dashboard | Overview and statistics, attendance overview, financial overview, plus the full **Baby Care Dashboard** (13 cards, 5 charts) |
| Parents & Children | Parents (Customer), Children, Enrollment, Classes & Groups, Teacher Assignments, Age Groups |
| Subscriptions & Billing | Plans, Child Subscriptions, Sales Invoices, Payment Entries, Outstanding Payments, Parent Account Statement |
| Health & Documents | Medical Records, Health Incidents, Vaccination Records, Child & Parent Documents, Document Alerts |
| Services & Activities | Services, Child-Specific Services, Meal Plans, Child Meal Plans, Daily Meal List, Transport |
| Staff & Attendance | Teachers, Staff (ERPNext Employee), Child Attendance, Daily Attendance Report |
| Reports | 9 script reports (below) |
| Configuration | Settings, plans, categories, transport, classes, age groups, document types, statuses, **Role Permissions Manager**, User Permissions |
| Data Management | Seed / test data page |

The workspace is rebuilt on every `migrate`. Each link is checked against the database first, so a
missing DocType, report or page never becomes a dead link. Links a user cannot open are hidden by Frappe.

---

## Reports

All reports read through `frappe.get_list`, so they apply the same row-level rules as list views.

| Report | For |
|---|---|
| Enrolled Children Summary | Children by class, teacher, age group and parent; next birthday; allergy flag |
| Attendance Summary | Daily records or per-child rates over a date range |
| Daily Meal List | Today's menu per child; the child's own plan overrides the global one; allergy alerts |
| Subscription Status Report | Status, days left, next billing date and expiring soon |
| Revenue Report | Nursery invoices grouped by month, quarter, plan, parent or child |
| Outstanding Payments | Unpaid nursery invoices with ageing buckets |
| Parent Account Statement | Invoices, payments, running balance and next due date for one parent |
| Medical and Document Alerts | Missing, expired or expiring documents, severe allergies, vaccinations due |
| Vaccination Status | Every vaccination with overdue or due-soon status |

---

## Roles and permissions

| Role | Access |
|---|---|
| System Manager | Everything |
| Nursery Administrator | Everything in the app, including settings and configuration |
| Nursery Accountant | Subscriptions, invoices, payments, finance reports. **No medical data** |
| Nursery Teacher | **Only assigned children**: primary teacher or class teacher. Attendance, meal plans, incidents for those children. No finance, no medical records |
| Nursery Medical Staff | Medical records and incidents for all children. **No finance** |
| Nursery Receptionist | Children, parents, enrollment, contacts, pickups, attendance. No medical or finance records |

How it is enforced, all on the server:

* **DocType permissions** decide who may open each DocType at all. They are editable in
  **Role Permissions Manager**, and the app never overwrites those edits on migrate.
* **Permission levels** on Child: medical notes are level 1 (admin and medical staff); subscription
  status is level 2 (admin, accountant, receptionist).
* **`permission_query_conditions` and `has_permission` hooks** narrow teacher-only users to their
  assigned children in list views, forms, direct URLs, reports, link search and `/api/resource`.
  They never grant access. If an administrator later gives teachers access to medical records,
  teachers still see only their own children's records.
* Install adds the nursery roles to ERPNext's Customer, Sales Invoice and Payment Entry, and only
  when the role has no rule there yet, plus the light *select* right on Account, Customer Group,
  Territory and Company so parents open without errors. Give accountants ERPNext's **Accounts User** role as well,
  and receptionists **Sales User**, so the linked ERPNext masters open for them.

---

## Billing

* Each Child Subscription is a submittable document: Draft → Active / Pending → Suspended / Expired / Cancelled.
* Its amount is the plan price, plus optional services, minus the discount. The family discount
  (Settings, or a per-plan override) is applied automatically to a second or further child of the same parent.
* **Generate Invoice** (or the daily job, when *Auto Generate Invoices* is on) creates a Sales Invoice
  for the next billing period. It carries a plan line, service lines, a transport line for the period,
  and the plan's ERPNext tax template.
* The invoice records the child, subscription and billing period in custom fields, so a period can
  never be invoiced twice. Cancelled or expired subscriptions are never invoiced.
* Payment Entries update each subscription's invoice status automatically.
* Renew, Suspend and Resume are buttons on the subscription. Auto-Renew plans renew in the daily job.

## Daily jobs and notifications

Pending subscriptions are activated and ended ones expire or auto-renew, then due invoices are
generated. Notification Logs (de-duplicated) cover: subscriptions expiring soon, expired
subscriptions, documents expiring or missing, overdue nursery invoices, upcoming birthdays, and
serious or emergency health incidents (sent immediately).

## Business rules

A child needs at least one parent, and only one primary parent. Only active teachers can be
assigned. Class capacity is enforced (switchable). A child has one attendance record per day, and
check-out requires an authorized pickup person (switchable). One medical record per child, with
history tracked. A child meal plan that contains one of the child's recorded allergens is rejected.
Subscriptions cannot overlap for the same child, and the parent must be linked to the child.
Transport routes respect capacity and stops. Expiry dates mark documents Expired automatically.

---

## Tests

```bash
bench --site <site> set-config allow_tests true
bench --site <site> run-tests --module baby_care.tests.test_baby_care
```

24 integration tests cover workspace integrity and desk rendering, number cards, invoice amounts and
family discount, duplicate-period protection, payment status sync, overlap and parent checks,
suspend/resume/renew, the business rules above, scheduler de-duplication and expiry, role access, and schema guards (valid table fields, no currency on count widgets).

## Languages

French and Arabic translations of the navigation and main messages ship in `baby_care/translations/`.

## Licence

MIT
