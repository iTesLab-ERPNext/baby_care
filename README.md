# Baby Care Management

A complete Nursery, Daycare & Childcare management application for **ERPNext v15 and v16**.

---

## Features

| Module | Highlights |
|---|---|
| **Child Management** | Full child profile, photo, enrollment, age-group, teacher assignment |
| **Parent Management** | ERPNext Customer DocType — children list, subscriptions, invoices shown inline |
| **Medical Records** | Allergies, vaccinations, medications, health incidents — role-restricted |
| **Subscriptions** | Flexible plans (monthly / quarterly / annual / custom), auto-invoice generation |
| **Billing** | ERPNext Sales Invoice & Payment Entry integration, multi-child discount |
| **Services** | Dynamic, administrator-configurable add-on services |
| **Meal Plans** | Global or child-specific, weekly menus, dietary restrictions |
| **Transportation** | Routes, stops, child assignments, fees |
| **Classes & Groups** | Capacity-enforced classes, multiple teachers |
| **Attendance** | Daily check-in/out, configurable statuses, duplicate prevention |
| **Documents** | Expiry tracking, private storage, mandatory-document rules |
| **Reports** | 4 built-in script reports; drill-down to ERPNext records |
| **Notifications** | Subscription expiry, document expiry, overdue invoice, birthday alerts |
| **Roles** | Administrator · Accountant · Teacher · Medical Staff · Receptionist |

---

## Installation

### Prerequisites
- ERPNext v15 or v16 installed in a Frappe bench
- Python ≥ 3.10, Node ≥ 18

### Steps

```bash
# 1. Get the app into your bench
bench get-app /path/to/baby_care
# or from a Git URL:
# bench get-app https://github.com/your-org/baby_care

# 2. Install onto your site
bench --site mysite.local install-app baby_care

# 3. Run migrations (also executes the patch to create seed data)
bench --site mysite.local migrate

# 4. Clear cache
bench --site mysite.local clear-cache

# 5. Build assets
bench build
```

### Post-install
1. Open **Baby Care Management** workspace.
2. Go to **Nursery Settings** and configure your facility name, company, billing account, and rules.
3. Create **Subscription Plans** for your fee structure.
4. Create **Age Groups**, **Nursery Classes**, and **Teacher Profiles**.
5. Register parents as ERPNext **Customers** (Customer Group: *Individual* recommended).
6. Create **Child** records and link them to parent customers.

---

## Running Tests

```bash
bench --site mysite.local run-tests --app baby_care
```

---

## Translation (i18n)

```bash
bench --site mysite.local export-translations --app baby_care --language fr
bench --site mysite.local export-translations --app baby_care --language ar
```

Edit the generated `.csv` files in `baby_care/translations/` and re-import with `import-translations`.

---

## Architecture

```
Customer (Parent)
  └── Child  (1..n)
        ├── Medical Record
        ├── Health Incident
        ├── Child Document
        ├── Child Attendance
        ├── Child Subscription  ──► Sales Invoice (ERPNext)
        ├── Child Meal Plan     ──► Meal Plan
        ├── Child Transportation ──► Transportation Route
        └── Child Service Assignment ──► Nursery Service

Nursery Class
  ├── Nursery Class Teacher  ──► Teacher Profile
  └── Nursery Class Child    ──► Child
```

---

## License
MIT
