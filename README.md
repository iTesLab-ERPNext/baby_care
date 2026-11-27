# Baby Care Management

Nursery, daycare, kindergarten and baby-care centre management on the **Frappe Framework (v15 / v16)**.
Since 2.0 the app is **independent of ERPNext**: parents, invoices and payments are the app's own
DocTypes (*Parent Profile*, *Nursery Invoice*, *Nursery Payment*). Only Frappe's own users, roles and
login are shared with the rest of the site. Every rule that varies between facilities is
configuration, not code.

Version 2.0.0 is tested end-to-end on a Frappe v15 site **without ERPNext**: fresh install, 49
automated tests, the Parent API (38 HTTP checks), the parent mobile app (23 browser checks) and a
desk walk-through (30 checks); and as an upgrade of a 1.6 site that has ERPNext installed.

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

Only the Frappe Framework is required (complete Frappe's setup wizard so a default currency exists).
ERPNext may be installed on the same site; Baby Care simply does not use it.

### Upgrading from 1.x (ERPNext) to 2.0

`git pull` (or replace the app folder) and run `bench --site <site> migrate`. What changes:

* New DocTypes **Parent Profile**, **Nursery Invoice** (+ items), **Nursery Payment** (+ allocations).
* Parents are now *Parent Profiles*. The "Parent (Customer)" links on Child, Child Subscription and
  Child Document become "Parent" links to Parent Profile. **Existing data is not copied** (fresh start):
  children, subscriptions, attendance, medical records… stay, but their parent link is empty. Create
  the Parent Profiles and set them on each child; on a submitted subscription without a parent the
  *Parent* field can be filled in once. Subscriptions without a parent are skipped by the daily
  invoice job.
* Invoices and payments are made in the app from now on. Old ERPNext Customers, Sales Invoices and
  Payment Entries are left untouched in ERPNext and are no longer shown by Baby Care.
* The app's custom fields on ERPNext's Customer and Sales Invoice are removed, the *Nursery Revenue*
  chart and all finance cards and reports now read Nursery Invoices.
* Parent App logins move from the Customer to the Parent Profile (**Parent App** tab): enable them
  again there. Old parent users keep existing but are no longer linked.

### First steps

1. **Baby Care Management → Data Management → Install Seed Data**: services, subscription plans,
   meal plans and a transport route you can edit.
2. Optional: **Install Test Data** loads tagged demo records for every part of the app: 4 parents
   (3 with mobile app logins), 5 children, 2 teachers and classes, 2 weeks of attendance, medical
   records, health notes, documents, meal plans, services, transport, subscriptions, invoices
   (paid, partly paid, unpaid, overdue) and payments. The page shows the demo logins:

   | Login | Password | Children |
   |---|---|---|
   | `sara@babycare.demo` | `BabyCare@2026` | Adam, Lina |
   | `karim@babycare.demo` | `BabyCare@2026` | Omar |
   | `amira@babycare.demo` | `BabyCare@2026` | Yasmine, Rayan |

   **Clear Test Data** removes exactly those records and logins (do it before going live).
   From the command line: `bench --site <site> execute baby_care.baby_care_management.api.seed.install_test_data`.
3. **Configuration → Application Settings**: set the currency, invoice due days, default tax, family
   discount, payment instructions (printed for parents), notification windows and the operational switches.
4. **Parents → New**: create a Parent Profile, then **Create → Register Child** from it.

---

## Workspace (`/app/baby-care-management`)

The top of the page shows 8 live number cards and 4 charts, followed by 8 shortcuts and 9 cards:

| Section | Links |
|---|---|
| Dashboard | Overview and statistics, attendance overview, financial overview, plus the full **Baby Care Dashboard** (13 cards, 5 charts) |
| Parents & Children | Parents, Children, Enrollment, Classes & Groups, Teacher Assignments, Age Groups |
| Subscriptions & Billing | Plans, Child Subscriptions, Invoices, Payments, Outstanding Payments, Parent Account Statement |
| Health & Documents | Medical Records, Health Incidents, Vaccination Records, Child & Parent Documents, Document Alerts |
| Services & Activities | Services, Child-Specific Services, Meal Plans, Child Meal Plans, Daily Meal List, Transport |
| Staff & Attendance | Teachers, Child Attendance, Daily Attendance Report |
| Reports | 9 script reports (below) |
| Configuration | Settings, plans, categories, transport, classes, age groups, document types, statuses, **Role Permissions Manager**, User Permissions |
| Data Management | Seed / test data page |

The workspace is rebuilt on every `migrate`. Each link is checked against the database first, so a
missing DocType, report or page never becomes a dead link. Links a user cannot open are hidden by Frappe.

### Navbar menu

A **Baby Care ▾** button next to the logo in the top bar opens the same sections and links as the
workspace, available on every desk page:

* each section expands and collapses; *Expand all / Collapse all*; open sections are remembered
  per browser, and the section of the page you are on opens automatically;
* a filter box narrows the links as you type (Enter opens the first match);
* the current page is highlighted; Ctrl/⌘/middle-click opens a link in a new tab; Esc or a click
  outside closes the panel; on phones it opens full-width.

### Nested sidebar menu

The same sections also appear in the left desk sidebar, nested under **Baby Care Management**:

* the chevron on the *Baby Care Management* item shows or hides the whole tree;
* each section expands and collapses on its own;
* both choices are remembered per browser; entering a Baby Care page opens the tree (unless you
  collapsed it yourself) and the section of the current page;
* the current page is highlighted, long names are shortened with a tooltip, and the tree survives
  Frappe rebuilding the sidebar.

All three menus are built on the server at login from the workspace definition and filtered by the
user's permissions, so they never list a page the user cannot open. Users without a Baby Care role
see none of them.

---

## Parent API (mobile app / parent portal)

A read-only REST API for parents.

* **Inside the desk:** **Baby Care → Configuration → Parent API** (`/app/parent-api`) lists every
  endpoint with search and group filter; click a row for its URL, parameters and examples.
  System Manager and Nursery Administrator only.
* **Public documentation** with a built-in *Try it* console: **`https://<your-site>/parent-api`**
  (website URL, not under `/app`). Machine-readable OpenAPI 3 (Swagger UI, Postman, Insomnia):
**`/api/method/baby_care.api.v1.openapi`**.

| Endpoint | Method | What it returns |
|---|---|---|
| `app_login` | POST | **mobile app:** token, parent profiles, children (see *Parent mobile app*) |
| `app_logout` | POST | mobile app: forget this phone, or sign out everywhere (`all_devices=1`) |
| `change_password` | POST | mobile app: new password, returns a new token |
| `register_device` | POST | mobile app: store the Expo push token of the phone |
| `notifications` | GET | activity feed: arrivals, departures, absences, incidents, invoices, payments, reminders |
| `app_info` | GET | public: nursery name, logo, currency (shown on the login screen) |
| `login` | POST | session (`sid`), CSRF token, parent profiles, children |
| `logout` | POST | ends the session |
| `me` | GET | parent profile and children |
| `children` | GET | my children with class, teacher, status |
| `child` | GET | full profile: teachers, emergency contacts, pickups, allergies, vaccinations, subscription |
| `child_tracking` | GET | daily follow-up: arrival/departure/pickup, today's menu, incidents, 30-day attendance rate, vaccinations, document alerts |
| `child_attendance` | GET | attendance history + summary (date range, paging) |
| `child_meals` | GET | menu of the day (child's own plan or the nursery menu) |
| `child_incidents` | GET | health incidents |
| `child_documents` | GET | documents on file and missing mandatory documents |
| `subscriptions` | GET | subscriptions of my children |
| `invoices` / `invoice` | GET | invoices (`status` = all, unpaid, overdue, paid) and one invoice with lines and payments |
| `payments` | GET | payments with the invoices they settle |
| `balance` | GET | invoiced, paid, outstanding, overdue, next due date, per child |

All URLs are `/api/method/baby_care.api.v1.<endpoint>`; results are wrapped in `message`.

**Giving a parent access:** open the Parent Profile → **Parent App** tab (or the **Enable
Parent App** button). See *Parent mobile app* below.

**Security:**
* a parent only ever sees the children, invoices and payments of their own Parent Profile; another
  family's child or invoice answers `404`, so records cannot be probed;
* everything except `login` / `logout` is GET-only; POSTs with a session need the CSRF token;
* `login` and `app_login` are limited to 10 attempts per 5 minutes per IP;
* staff accounts that are not linked to a parent cannot log in through the API;
* server-to-server clients can use Frappe API keys: `Authorization: token <api_key>:<api_secret>`;
* use HTTPS in production. For a web app on another domain, allow it with `allow_cors` in
  `site_config.json` (`bench --site <site> set-config allow_cors "https://app.example.com"`);
  native mobile apps need nothing extra.

## Parent mobile app

The **BabyCare** parent app (React Native / **Expo SDK 58**, JavaScript) ships in the separate
`babycare` project (see its README). It uses the Parent API above and sends its language in the
`X-BabyCare-Lang` header (`fr`, `en`, `ar`), so feed texts and messages come back in that language.

**Logins are managed on the Parent Profile**, **Parent App** tab (one login per parent):

| Field | |
|---|---|
| Enable Parent App Access | switches the login on / off. Off disables the user and signs out every phone. |
| App Login (e-mail) | the username. Defaults to the parent's e-mail. Changing it renames the user (password kept). |
| Set / Change Password | type a password and save. It is applied to the user and **never stored on the profile**. Minimum 8 characters + the site's password policy. |
| E-mail the login details to the parent | sends the login (and a generated password, if one was made) on save. |
| Linked App User | read-only: the Frappe User created for the parent. |

* **Automatic creation:** when a child is saved, every active parent of that child that has an
  e-mail and no app login gets one: a Frappe *Website User* (no desk) with the **Nursery Parent**
  role, linked in the profile's *Linked App User*. A generated password is shown **once** to the
  staff member. Switch this off in **Nursery Settings → Parent App**. An access you switched off is
  not re-enabled.
* **Generate New App Password** (Parent App menu on the profile): new random password, shown once;
  the parent is signed out on every phone.
* **Two parents of one child** = two Parent Profiles linked on the child, each with its own login;
  both see the same child. An e-mail can be the login of one profile only.
* Deactivating or deleting a profile also switches its login off.

**How the app signs in:** `app_login` checks the password with Frappe's own login checks (lockout,
disabled users) and returns `api_key:api_secret` for `Authorization: token …`; no cookie or CSRF.
Changing the password, *sign out on all devices*, a password set by staff and switching access
off all rotate the secret, so old tokens stop working at once.

**Push notifications** (Expo): the app registers its push token (`register_device`, DocType
*Parent App Device*). Parents are notified when their child arrives or is picked up, is marked
absent, on a new health incident, a new invoice and a payment received. Sends run in the
background queue after commit; tokens Expo reports as gone are disabled. Switch off in
**Nursery Settings → Parent App**.

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
* **Parent Profile**: administrators full; accountants and receptionists create and edit;
  teachers and medical staff read only. **Nursery Invoice**: administrators and accountants
  (receptionists read). **Nursery Payment**: administrators, accountants and receptionists can
  record and submit payments.

---

## Billing

* Each Child Subscription is a submittable document: Draft → Active / Pending → Suspended / Expired / Cancelled.
* Its amount is the plan price, plus optional services, minus the discount. The family discount
  (Settings, or a per-plan override) is applied automatically to a second or further child of the same parent.
* **Generate Invoice** (or the daily job, when *Auto Generate Invoices* is on) creates a **Nursery
  Invoice** for the next billing period: a plan line, service lines and a transport line for the
  period, the subscription's discount and the plan's tax (or the default tax of the settings).
  A billing period can never be invoiced twice. Cancelled or expired subscriptions are never invoiced.
* Invoices can also be made by hand (any lines, discount %, tax %). Status: Draft → Unpaid →
  Partly Paid → Paid, or Overdue after the due date; Cancelled.
* **Nursery Payment** records money received (cash, transfer, card, cheque, mobile payment). It is
  allocated to invoices of that parent: pick them, use **Get Unpaid Invoices**, or leave the table
  empty to settle the oldest due first. Anything not allocated stays as a **credit** of the parent.
  **Record Payment** on an invoice opens a payment already filled in.
* Paid amount, outstanding amount and status of each invoice, and of the subscription's invoice
  list, follow the submitted payments. Cancel the payments before cancelling an invoice.
* Renew, Suspend and Resume are buttons on the subscription. Auto-Renew plans renew in the daily job.
* There is no accounting ledger: if you need one, export the invoices and payments lists.

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

49 integration tests cover workspace integrity and desk rendering, number cards, invoice amounts and
family discount, duplicate-period protection, partial / full / over-payments, oldest-first allocation
and credit, tax and discount, overdue status, invoice cancel rules, overlap and parent checks,
suspend/resume/renew, the business rules above, scheduler de-duplication and expiry, role access,
schema guards (valid table fields, no currency on count widgets), the Parent API family isolation,
and the Parent App credentials (password from the form, weak/staff logins refused, login rename,
token rotation, device registration, disabling, automatic logins), the 1.x upgrade case (subscription
without parent) and a guard that no DocType of the app links to an ERPNext DocType.

Run them on any Frappe site; ERPNext is not needed.

## Languages

French and Arabic translations of the navigation and main messages ship in `baby_care/translations/`.

## Licence

MIT
