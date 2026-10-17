"""
Row-level permissions for Baby Care Management.

Two layers, both server-side:

* ``permission_query_conditions`` — SQL fragments appended to list views,
  reports built on ``frappe.get_list``, link search and ``/api/resource``.
* ``has_permission`` — document-level checks used by form views, direct URLs,
  ``frappe.get_doc(...).check_permission()`` and ``/api/resource/<dt>/<name>``.

DocType-level access (which role may read / write / create a DocType at all)
stays in the standard DocType permissions and is editable from Role
Permissions Manager. These hooks only *narrow* access for restricted roles;
they never grant access the DocType permissions do not already give.

Unrestricted roles (System Manager, Nursery Administrator, Administrator)
always short-circuit to "no extra filter".
"""
import frappe

ADMIN_ROLES = {"System Manager", "Nursery Administrator"}
TEACHER_ROLE = "Nursery Teacher"

# Roles that see every child row (column access is still governed by
# DocType permissions and permission levels).
ALL_CHILDREN_ROLES = {"Nursery Receptionist", "Nursery Medical Staff", "Nursery Accountant"}


# ── helpers ──────────────────────────────────────────────────────────────────
def _user(user=None):
    return user or frappe.session.user


def _roles(user):
    return set(frappe.get_roles(user))


def is_admin(user=None):
    user = _user(user)
    if user == "Administrator":
        return True
    return bool(_roles(user) & ADMIN_ROLES)


# Backwards-compatible alias used by older code paths.
_is_admin = is_admin


def get_teacher_profile(user=None):
    return frappe.db.get_value("Teacher Profile", {"user_account": _user(user)}, "name")


def get_teacher_classes(teacher):
    if not teacher:
        return []
    return frappe.get_all(
        "Nursery Class Teacher",
        filters={"teacher": teacher, "parenttype": "Nursery Class"},
        pluck="parent",
    )


def get_teacher_children(user=None):
    """Children a teacher may see: primary assignment + children of classes they teach."""
    teacher = get_teacher_profile(user)
    if not teacher:
        return []
    names = set(frappe.get_all("Child", filters={"assigned_teacher": teacher}, pluck="name"))
    classes = get_teacher_classes(teacher)
    if classes:
        names.update(frappe.get_all("Child", filters={"nursery_class": ("in", classes)}, pluck="name"))
    return sorted(names)


def _in_clause(table, field, values):
    if not values:
        return "1=0"
    escaped = ", ".join(frappe.db.escape(v) for v in values)
    return f"`tab{table}`.`{field}` in ({escaped})"


def _teacher_only(user):
    """True when the user's only reason to see child data is the teacher role."""
    roles = _roles(user)
    return TEACHER_ROLE in roles and not (roles & (ADMIN_ROLES | ALL_CHILDREN_ROLES))


def has_app_permission():
    """Show the app tile on /apps to users holding any Baby Care role."""
    roles = _roles(frappe.session.user)
    return frappe.session.user == "Administrator" or bool(roles & (ADMIN_ROLES | ALL_CHILDREN_ROLES | {TEACHER_ROLE}))


# ── Child ────────────────────────────────────────────────────────────────────
def get_child_access_conditions(user=None):
    user = _user(user)
    if is_admin(user) or not _teacher_only(user):
        return ""
    teacher = get_teacher_profile(user)
    if not teacher:
        return "1=0"
    cond = f"`tabChild`.`assigned_teacher` = {frappe.db.escape(teacher)}"
    classes = get_teacher_classes(teacher)
    if classes:
        cond = f"({cond} or {_in_clause('Child', 'nursery_class', classes)})"
    return cond


def has_child_permission(doc, ptype=None, user=None, **kwargs):
    user = _user(user)
    if is_admin(user) or not _teacher_only(user):
        return True
    return doc.name in get_teacher_children(user)


# ── records that hang off a child (attendance, meal plans, transport…) ───────
def _child_linked_conditions(doctype, user):
    user = _user(user)
    if is_admin(user) or not _teacher_only(user):
        return ""
    return _in_clause(doctype, "child", get_teacher_children(user))


def _child_linked_permission(doc, user):
    user = _user(user)
    if is_admin(user) or not _teacher_only(user):
        return True
    if not doc.get("child"):
        # New, still-empty form: allow so the teacher can pick a child;
        # the save is re-checked once `child` is set.
        return doc.is_new()
    return doc.child in get_teacher_children(user)


def get_attendance_conditions(user=None):
    return _child_linked_conditions("Child Attendance", user)


def has_attendance_permission(doc, ptype=None, user=None, **kwargs):
    return _child_linked_permission(doc, user)


def get_child_meal_plan_conditions(user=None):
    return _child_linked_conditions("Child Meal Plan", user)


def has_child_meal_plan_permission(doc, ptype=None, user=None, **kwargs):
    return _child_linked_permission(doc, user)


def get_child_transportation_conditions(user=None):
    return _child_linked_conditions("Child Transportation", user)


def has_child_transportation_permission(doc, ptype=None, user=None, **kwargs):
    return _child_linked_permission(doc, user)


def get_child_service_conditions(user=None):
    return _child_linked_conditions("Child Service Assignment", user)


def has_child_service_permission(doc, ptype=None, user=None, **kwargs):
    return _child_linked_permission(doc, user)


# ── Medical Record / Health Incident / Child Document ───────────────────────
# Who may open these DocTypes at all is decided by the DocType permissions
# (Medical Record ships with System Manager, Nursery Administrator and
# Nursery Medical Staff only) and can be changed in Role Permissions Manager.
# The hooks only narrow teacher-only users to their assigned children, so
# granting a teacher access later never exposes other children's records.
def get_medical_record_access_conditions(user=None):
    return _child_linked_conditions("Medical Record", user)


def has_medical_record_permission(doc, ptype=None, user=None, **kwargs):
    return _child_linked_permission(doc, user)


def get_health_incident_conditions(user=None):
    return _child_linked_conditions("Health Incident", user)


def has_health_incident_permission(doc, ptype=None, user=None, **kwargs):
    return _child_linked_permission(doc, user)


def get_child_document_conditions(user=None):
    user = _user(user)
    if is_admin(user) or not _teacher_only(user):
        return ""
    return _in_clause("Child Document", "child", get_teacher_children(user))


def has_child_document_permission(doc, ptype=None, user=None, **kwargs):
    if doc.get("document_for") == "Parent":
        user = _user(user)
        return is_admin(user) or not _teacher_only(user)
    return _child_linked_permission(doc, user)
