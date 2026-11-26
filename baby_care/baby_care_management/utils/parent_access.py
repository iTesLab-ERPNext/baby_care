"""
Parent App access — login credentials for parents, managed on the Customer.

Custom fields on Customer (tab "Parent App", created on install/migrate):
  bc_parent_app_access   Check     Enable Parent App Access
  bc_parent_login        Data      App Login (e-mail)
  bc_parent_password     Password  Set / Change Password   (never stored: applied to the user, then cleared)
  bc_send_credentials    Check     E-mail the login details to the parent
  bc_parent_user         Link User Linked App User (read only)

Rules
* Enabling access creates (or reuses) a Website User with the "Nursery Parent"
  role and adds it to the Customer's Portal Users — the link the Parent API
  uses to decide which children a parent sees.
* No password typed → a password is generated and shown once to the staff
  member who saved the form (and e-mailed if asked).
* Changing the login e-mail renames the user; disabling access disables the
  user (data and history stay).
* When a Child is saved, its parents that have an e-mail but no app login get
  one automatically (Nursery Settings → "Create Parent App Logins Automatically").
"""
import secrets
import string

import frappe
from frappe import _
from frappe.utils import cint, escape_html, get_url, validate_email_address

PARENT_ROLE = "Nursery Parent"
FIELDS = [
    {"fieldname": "bc_parent_app_tab", "fieldtype": "Tab Break", "label": "Parent App"},
    {"fieldname": "bc_parent_app_access", "fieldtype": "Check", "label": "Enable Parent App Access",
     "description": "Lets this parent sign in to the Baby Care mobile app and see only their own children, attendance, meals and invoices."},
    {"fieldname": "bc_parent_login", "fieldtype": "Data", "options": "Email", "label": "App Login (e-mail)",
     "depends_on": "bc_parent_app_access", "mandatory_depends_on": "bc_parent_app_access",
     "description": "Defaults to the customer's e-mail. Changing it changes the parent's login."},
    {"fieldname": "bc_parent_password", "fieldtype": "Password", "label": "Set / Change Password",
     "depends_on": "bc_parent_app_access",
     "description": "Leave empty to keep the current password. On first activation an empty password is generated and shown once."},
    {"fieldname": "bc_send_credentials", "fieldtype": "Check", "label": "E-mail the login details to the parent",
     "depends_on": "bc_parent_app_access"},
    {"fieldname": "bc_parent_app_col", "fieldtype": "Column Break"},
    {"fieldname": "bc_parent_user", "fieldtype": "Link", "options": "User", "label": "Linked App User", "read_only": 1,
     "depends_on": "bc_parent_user"},
]


def custom_fields(insert_after):
    out, prev = [], insert_after
    for df in FIELDS:
        row = dict(df, insert_after=prev)
        out.append(row)
        prev = df["fieldname"]
    return out


def generate_password(length=10):
    """Readable but strong: letters, digits and one symbol, no look-alikes."""
    alphabet = "".join(c for c in string.ascii_letters + string.digits if c not in "0O1lI")
    core = [secrets.choice(alphabet) for _ in range(length - 2)]
    core += [secrets.choice(string.digits[2:]), secrets.choice("@#%+")]
    secrets.SystemRandom().shuffle(core)
    return "".join(core)


def _masked(value):
    return not value or set(str(value)) == {"*"}


# ── Customer hooks ───────────────────────────────────────────────────────────
def customer_validate(doc, method=None):
    if not doc.meta.has_field("bc_parent_app_access"):
        return
    # take the typed password out of the document before it is saved
    pwd = doc.get("bc_parent_password")
    doc.flags.bc_new_password = None if _masked(pwd) else pwd
    doc.bc_parent_password = None
    if cint(doc.bc_parent_app_access):
        if not doc.bc_parent_login:
            doc.bc_parent_login = doc.email_id
        doc.bc_parent_login = (doc.bc_parent_login or "").strip().lower()
        if not doc.bc_parent_login or not validate_email_address(doc.bc_parent_login):
            frappe.throw(_("Enter a valid e-mail as the Parent App login."), title=_("Parent App"))
        owner = frappe.db.get_value("User", doc.bc_parent_login, ["name", "user_type"], as_dict=True)
        if owner and owner.user_type == "System User":
            frappe.throw(_("{0} is a staff account and cannot be used as a parent login.").format(doc.bc_parent_login), title=_("Parent App"))
        if doc.flags.bc_new_password:
            _check_strength(doc.flags.bc_new_password, doc.bc_parent_login)


def customer_on_update(doc, method=None):
    if not doc.meta.has_field("bc_parent_app_access") or doc.flags.bc_syncing:
        return
    # the masked value Frappe kept for the Password field is not wanted
    frappe.db.delete("__Auth", {"doctype": "Customer", "name": doc.name, "fieldname": "bc_parent_password"})
    if cint(doc.bc_parent_app_access):
        result = enable_access(doc, password=doc.flags.bc_new_password, send_email=cint(doc.bc_send_credentials))
        if doc.bc_send_credentials:
            frappe.db.set_value("Customer", doc.name, "bc_send_credentials", 0, update_modified=False)
        _report(result)
    elif doc.get_doc_before_save() and cint(doc.get_doc_before_save().get("bc_parent_app_access")):
        disabled = disable_access(doc.name)
        if disabled:
            frappe.msgprint(_("Parent App access disabled for {0}.").format(", ".join(disabled)), alert=True)


def disable_access(customer):
    """Switch off the app logins of a family: the main one and any extra Portal
    User that is a parent of this Customer only. Phones are signed out at once."""
    main = frappe.db.get_value("Customer", customer, "bc_parent_user")
    users = set(frappe.get_all("Portal User", {"parent": customer, "parenttype": "Customer"}, pluck="user"))
    if main:
        users.add(main)
    disabled = []
    for u in sorted(users):
        if u != main:
            if PARENT_ROLE not in frappe.get_roles(u):
                continue
            others = frappe.get_all("Portal User", {"user": u, "parenttype": "Customer", "parent": ("!=", customer)}, pluck="parent")
            if others:
                continue
        if frappe.db.get_value("User", u, "user_type") == "System User":
            continue
        if frappe.db.get_value("User", u, "enabled"):
            frappe.db.set_value("User", u, "enabled", 0)
            disabled.append(u)
        _rotate_api_secret(u)
        frappe.db.delete("Parent App Device", {"user": u})
    return disabled


def _report(result):
    if not result:
        return
    if result.get("password_generated"):
        frappe.msgprint(
            _("Parent App login created.<br><br><b>Login:</b> {0}<br><b>Password:</b> <code>{1}</code><br><br>"
              "Give these to the parent now — the password is not shown again. You can set a new one at any time in the Parent App tab.").format(
                escape_html(result["user"]), escape_html(result["password_generated"])),
            title=_("Parent App"), indicator="green",
        )
    elif result.get("password_changed"):
        frappe.msgprint(_("Parent App password updated for {0}.").format(result["user"]), alert=True, indicator="green")
    elif result.get("created") or result.get("renamed"):
        frappe.msgprint(_("Parent App login ready: {0}").format(result["user"]), alert=True, indicator="green")
    if result.get("emailed"):
        frappe.msgprint(_("Login details e-mailed to {0}.").format(result["user"]), alert=True)


def _check_strength(password, email):
    if len(password) < 8:
        frappe.throw(_("The password must have at least 8 characters."), title=_("Parent App"))
    from frappe.core.doctype.user.user import test_password_strength

    result = test_password_strength(password, user_data=(email,)) or {}
    feedback = result.get("feedback") or {}
    if cint(frappe.db.get_single_value("System Settings", "enable_password_policy")) and not feedback.get("password_policy_validation_passed", True):
        frappe.throw(_("The password is too weak. {0}").format(feedback.get("warning") or ""), title=_("Parent App"))


# ── core ─────────────────────────────────────────────────────────────────────
def enable_access(customer, password=None, send_email=False, login=None, additional=False):
    """Create / update the parent's login for a Customer. Returns what happened.

    additional=True adds another login to the family (Portal Users) and leaves
    the Customer's main Parent App login as it is."""
    cust = customer if not isinstance(customer, str) else frappe.get_doc("Customer", customer)
    login = (login or cust.get("bc_parent_login") or cust.email_id or "").strip().lower()
    if not login or not validate_email_address(login):
        frappe.throw(_("Customer {0} has no valid e-mail for the Parent App login.").format(cust.name))
    result = {"customer": cust.name, "user": login, "created": False, "renamed": False,
              "password_generated": None, "password_changed": False, "emailed": False}

    current = None if additional else cust.get("bc_parent_user")
    if current and current != login and frappe.db.exists("User", current) and not frappe.db.exists("User", login):
        frappe.rename_doc("User", current, login, force=True, show_alert=False)
        frappe.db.set_value("User", login, "email", login)
        result["renamed"] = True

    if frappe.db.exists("User", login):
        user = frappe.get_doc("User", login)
        if user.user_type == "System User":
            frappe.throw(_("{0} is a staff account and cannot be used as a parent login.").format(login))
        if not user.enabled:
            user.enabled = 1
            user.save(ignore_permissions=True)
    else:
        names = (cust.customer_name or login).split(" ", 1)
        user = frappe.get_doc({
            "doctype": "User",
            "email": login,
            "first_name": names[0][:140],
            "last_name": names[1][:140] if len(names) > 1 else "",
            "user_type": "Website User",
            "send_welcome_email": 0,
            "enabled": 1,
        })
        user.flags.ignore_permissions = True
        user.flags.no_welcome_mail = True
        user.insert()
        result["created"] = True
        if not password:
            password = generate_password()
            result["password_generated"] = password

    if PARENT_ROLE not in frappe.get_roles(user.name):
        user.flags.ignore_permissions = True
        user.add_roles(PARENT_ROLE)

    if password:
        from frappe.utils.password import update_password

        update_password(user.name, password)
        _rotate_api_secret(user.name)  # sign out the old mobile sessions
        result["password_changed"] = not result["password_generated"]

    # Portal Users link (what the Parent API reads)
    linked = frappe.get_all("Portal User", filters={"parent": cust.name, "parenttype": "Customer"}, pluck="user")
    if user.name not in linked:
        portal = frappe.get_doc({"doctype": "Portal User", "parent": cust.name, "parenttype": "Customer",
                                 "parentfield": "portal_users", "user": user.name, "idx": len(linked) + 1})
        portal.db_insert()
    if current and current != user.name and not result["renamed"]:
        frappe.db.delete("Portal User", {"parent": cust.name, "parenttype": "Customer", "user": current})

    if not (additional and cust.get("bc_parent_user")):
        frappe.db.set_value("Customer", cust.name, {"bc_parent_app_access": 1, "bc_parent_login": user.name, "bc_parent_user": user.name},
                            update_modified=False)
    if send_email:
        result["emailed"] = _send_credentials(cust, user.name, password)
    return result


def _rotate_api_secret(user):
    if frappe.db.get_value("User", user, "api_key"):
        from frappe.utils.password import set_encrypted_password

        set_encrypted_password("User", user, frappe.generate_hash(length=15), "api_secret")


def _send_credentials(cust, user, password):
    app = frappe.db.get_single_value("Nursery Settings", "facility_name") or _("Baby Care")
    lines = [
        _("Hello {0},").format(escape_html(cust.customer_name or "")),
        _("You can now follow your children with the {0} mobile app.").format(escape_html(app)),
        "<b>{0}</b> {1}<br><b>{2}</b> {3}".format(_("Server:"), escape_html(get_url()), _("Login:"), escape_html(user)),
    ]
    if password:
        lines.append("<b>{0}</b> {1}".format(_("Password:"), escape_html(password)))
    else:
        lines.append(_("Use your current password, or ask the nursery to set a new one."))
    lines.append(_("Please change your password after your first login (Profile → Change password)."))
    try:
        frappe.sendmail(recipients=[user], subject=_("{0} — your parent app login").format(app),
                        message="<p>" + "</p><p>".join(lines) + "</p>", delayed=False)
        return True
    except Exception:
        frappe.log_error(title="Baby Care: could not e-mail parent credentials")
        frappe.msgprint(_("The login details could not be e-mailed (check the outgoing e-mail account)."), indicator="orange")
        return False


# ── Child hook: automatic creation ───────────────────────────────────────────
def child_on_update(doc, method=None):
    if not cint(frappe.db.get_single_value("Nursery Settings", "auto_create_parent_login")):
        return
    if not frappe.get_meta("Customer").has_field("bc_parent_app_access"):
        return
    for row in doc.get("parents") or []:
        info = frappe.db.get_value("Customer", row.parent_customer,
                                   ["name", "email_id", "bc_parent_app_access", "bc_parent_user"], as_dict=True)
        if not info or info.bc_parent_user or info.bc_parent_app_access is None:
            continue
        if cint(info.bc_parent_app_access) == 0 and frappe.db.get_value("Customer", info.name, "bc_parent_login"):
            continue  # access was switched off on purpose
        email = (info.email_id or "").strip().lower()
        if not email or not validate_email_address(email):
            continue
        owner_type = frappe.db.get_value("User", email, "user_type")
        if owner_type == "System User":
            continue
        try:
            _report(enable_access(info.name, login=email))
        except Exception:
            frappe.log_error(title=f"Baby Care: automatic parent login failed for {info.name}")


# ── staff API (Customer form buttons) ────────────────────────────────────────
@frappe.whitelist(methods=["POST"])
def reset_parent_password(customer, password=None, send_email=0):
    """Set a new password (or generate one) for the parent's app login."""
    frappe.has_permission("Customer", "write", customer, throw=True)
    cust = frappe.get_doc("Customer", customer)
    if not cint(cust.get("bc_parent_app_access")) or not cust.get("bc_parent_user"):
        frappe.throw(_("Enable Parent App access for this customer first."))
    generated = None
    if not password:
        password = generated = generate_password()
    _check_strength(password, cust.bc_parent_user)
    from frappe.utils.password import update_password

    update_password(cust.bc_parent_user, password)
    _rotate_api_secret(cust.bc_parent_user)
    emailed = _send_credentials(cust, cust.bc_parent_user, password) if cint(send_email) else False
    return {"user": cust.bc_parent_user, "password": generated, "emailed": emailed}
