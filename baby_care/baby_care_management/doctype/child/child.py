import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today, cint


def age_in_months(dob, on=None):
    dob = getdate(dob)
    on = getdate(on or today())
    months = (on.year - dob.year) * 12 + (on.month - dob.month)
    if on.day < dob.day:
        months -= 1
    return max(months, 0)


class Child(Document):
    def validate(self):
        self.first_name = (self.first_name or "").strip()
        self.last_name = (self.last_name or "").strip()
        self.full_name = f"{self.first_name} {self.last_name}".strip()
        self._validate_dates()
        self._set_age_display()
        self._set_age_group()
        self._validate_parents()
        self._validate_enrollment()
        self._validate_teacher()
        self._validate_class_capacity()

    def on_update(self):
        self._sync_class_membership()

    def on_trash(self):
        self._remove_from_classes()

    # ── validation ───────────────────────────────────────────────────────
    def _validate_dates(self):
        if self.date_of_birth and getdate(self.date_of_birth) > getdate(today()):
            frappe.throw(_("Date of birth cannot be in the future."))
        if self.registration_date and self.date_of_birth and getdate(self.registration_date) < getdate(self.date_of_birth):
            frappe.throw(_("Registration date cannot be before the date of birth."))

    def _set_age_display(self):
        if not self.date_of_birth:
            self.age_display = ""
            return
        months = age_in_months(self.date_of_birth)
        years, rem = divmod(months, 12)
        self.age_display = _("{0} yr {1} mo").format(years, rem) if years else _("{0} mo").format(rem)

    def _set_age_group(self):
        if self.age_group or not self.date_of_birth:
            return
        months = age_in_months(self.date_of_birth)
        group = frappe.db.sql(
            """select name from `tabAge Group`
               where is_active = 1 and ifnull(min_age_months, 0) <= %(m)s
                 and (ifnull(max_age_months, 0) = 0 or max_age_months > %(m)s)
               order by min_age_months desc limit 1""",
            {"m": months},
        )
        if group:
            self.age_group = group[0][0]

    def _validate_parents(self):
        if not self.parents:
            frappe.throw(_("A child must have at least one parent or guardian linked."))
        seen = set()
        for row in self.parents:
            if row.parent_customer in seen:
                frappe.throw(_("Parent {0} is linked more than once.").format(row.parent_customer))
            seen.add(row.parent_customer)
        primaries = [p for p in self.parents if p.is_primary]
        if not primaries:
            self.parents[0].is_primary = 1
        elif len(primaries) > 1:
            frappe.throw(_("Only one parent can be marked as primary."))

    def _validate_enrollment(self):
        if self.enrollment_status == "Active" and not self.registration_date:
            self.registration_date = today()

    def _validate_teacher(self):
        if not self.assigned_teacher:
            return
        status = frappe.db.get_value("Teacher Profile", self.assigned_teacher, "employment_status")
        if status != "Active" and self.has_value_changed("assigned_teacher"):
            frappe.throw(_("Teacher {0} is not active and cannot be assigned.").format(self.assigned_teacher))

    def _validate_class_capacity(self):
        if not self.nursery_class or self.enrollment_status not in ("Active", "Pending"):
            return
        if not cint(frappe.db.get_single_value("Nursery Settings", "enforce_class_capacity")):
            return
        if not (self.has_value_changed("nursery_class") or self.has_value_changed("enrollment_status")):
            return
        capacity, status = frappe.db.get_value("Nursery Class", self.nursery_class, ["capacity", "status"])
        if status == "Inactive":
            frappe.throw(_("Class {0} is inactive.").format(self.nursery_class))
        if not cint(capacity):
            return
        enrolled = frappe.db.count(
            "Child",
            {"nursery_class": self.nursery_class, "enrollment_status": ("in", ["Active", "Pending"]),
             "name": ("!=", self.name or "")},
        )
        if enrolled >= cint(capacity):
            frappe.throw(_("Class {0} is full ({1}/{2}).").format(self.nursery_class, enrolled, capacity))

    # ── class membership (keeps Nursery Class.children in sync) ──────────
    def _sync_class_membership(self):
        before = self.get_doc_before_save()
        old_class = before.nursery_class if before else None
        if old_class and old_class != self.nursery_class:
            _set_class_row(old_class, self.name, "Withdrawn")
        if self.nursery_class:
            status = "Active" if self.enrollment_status in ("Active", "Pending") else "Withdrawn"
            _set_class_row(self.nursery_class, self.name, status)

    def _remove_from_classes(self):
        for cls in frappe.get_all("Nursery Class Child", filters={"child": self.name}, pluck="parent"):
            doc = frappe.get_doc("Nursery Class", cls)
            doc.children = [r for r in doc.children if r.child != self.name]
            doc.flags.ignore_permissions = True
            doc.save()

    # ── API used by the form ─────────────────────────────────────────────
    @frappe.whitelist()
    def get_profile_summary(self):
        """Counts and highlights for the child dashboard (permission aware)."""
        out = {"attendance": [], "alerts": []}
        if frappe.has_permission("Child Attendance", "read"):
            out["attendance"] = frappe.get_list(
                "Child Attendance",
                filters={"child": self.name},
                fields=["attendance_date", "status", "check_in_time", "check_out_time"],
                order_by="attendance_date desc",
                limit_page_length=10,
            )
        if self.has_allergies:
            out["alerts"].append(_("This child has recorded allergies — check the medical record before serving food or medication."))
        if frappe.has_permission("Child Document", "read"):
            expired = frappe.get_list("Child Document", filters={"child": self.name, "status": ("in", ["Expired", "Missing"])}, pluck="document_type")
            if expired:
                out["alerts"].append(_("Documents expired or missing: {0}").format(", ".join(expired)))
        return out


def _set_class_row(class_name, child, status):
    if not frappe.db.exists("Nursery Class", class_name):
        return
    cls = frappe.get_doc("Nursery Class", class_name)
    row = next((r for r in cls.children if r.child == child), None)
    if row:
        if row.enrollment_status == status:
            return
        row.enrollment_status = status
    else:
        if status != "Active":
            return
        cls.append("children", {"child": child, "enrollment_status": "Active", "enrolled_on": today()})
    cls.flags.ignore_permissions = True
    cls.flags.from_child_sync = True
    cls.save()
