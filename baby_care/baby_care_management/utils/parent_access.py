"""
Parent App access — the parent's login, managed on the Parent Profile (tab "Parent App").

  app_access        Enable Parent App Access
  app_login         App Login (e-mail)
  app_password      Set / Change Password   (never stored: applied to the user, then cleared)
  send_credentials  E-mail the login details to the parent
  user              Linked App User (read only)

Rules
* Enabling access creates (or reuses) a Frappe *Website User* with the
  "Nursery Parent" role and links it in ``Parent Profile.user`` — the link the
  Parent API uses to decide which children a parent sees. One login per profile.
* No password typed for a new login → one is generated and shown once to the
  staff member who saved the form (and e-mailed if asked).
* Changing the login e-mail renames the user; switching access off disables the
  user, signs out every phone (token rotated, devices dropped).
* When a Child is saved, its parents that have an e-mail but no app login get
  one automatically (Nursery Settings → "Create Parent App Logins Automatically").
"""
import secrets
import string

import frappe
from frappe import _
from frappe.utils import cint, escape_html, get_url, validate_email_address

PARENT_ROLE = "Nursery Parent"
DT = "Parent Profile"


def generate_password(length=10):
    """Readable but strong: letters, digits and one symbol, no look-alikes."""
    alphabet = "".join(c for c in string.ascii_letters + string.digits if c not in "0O1lI")
    core = [secrets.choice(alphabet) for _ in range(length - 2)]
    core += [secrets.choice(string.digits[2:]), secrets.choice("@#%+")]
    secrets.SystemRandom().shuffle(core)
    return "".join(core)


def _masked(value):
    return not value or set(str(value)) == {"*"}


# ── Parent Profile hooks (called from its controller) ────────────────────────
def profile_validate(doc):
    pwd = doc.get("app_password")
    doc.flags.new_password = None if _masked(pwd) else pwd
    doc.app_password = None
    if not cint(doc.app_access):
        return
    doc.app_login = (doc.app_login or doc.email or "").strip().lower()
    if not doc.app_login or not validate_email_address(doc.app_login):
        frappe.throw(_("Enter a valid e-mail as the Parent App login."), title=_("Parent App"))
    owner = frappe.db.get_value("User", doc.app_login, ["name", "user_type"], as_dict=True)
    if owner and owner.user_type == "System User":
        frappe.throw(_("{0} is a staff account and cannot be used as a parent login.").format(doc.app_login), title=_("Parent App"))
    other = frappe.db.get_value(DT, {"user": doc.app_login, "name": ("!=", doc.name)}, "name") or (
        frappe.db.get_value(DT, {"app_login": doc.app_login, "app_access": 1, "name": ("!=", doc.name)}, "name"))
    if other:
        frappe.throw(_("{0} is already the app login of parent {1}.").format(doc.app_login, other), title=_("Parent App"))
    if doc.flags.new_password:
        check_strength(doc.flags.new_password, doc.app_login)


def profile_on_update(doc):
    if doc.flags.syncing_access:
        return
    frappe.db.delete("__Auth", {"doctype": DT, "name": doc.name, "fieldname": "app_password"})
    if cint(doc.app_access):
        result = enable_access(doc, password=doc.flags.new_password, send_email=cint(doc.send_credentials))
        if doc.send_credentials:
            frappe.db.set_value(DT, doc.name, "send_credentials", 0, update_modified=False)
        _report(result)
    else:
        before = doc.get_doc_before_save()
        if (before and cint(before.app_access)) or (not cint(doc.is_active) and doc.user):
            disabled = disable_access(doc.name)
            if disabled:
                frappe.msgprint(_("Parent App access disabled for {0}.").format(", ".join(disabled)), alert=True)


def profile_on_trash(doc):
    if doc.user:
        disable_access(doc.name)


def disable_access(parent_profile):
    """Switch off a parent's login; phones are signed out at once. Returns the users disabled."""
    user = frappe.db.get_value(DT, parent_profile, "user")
    if not user or not frappe.db.exists("User", user) or frappe.db.get_value("User", user, "user_type") == "System User":
        return []
    disabled = []
    if frappe.db.get_value("User", user, "enabled"):
        frappe.db.set_value("User", user, "enabled", 0)
        disabled.append(user)
    rotate_api_secret(user)
    frappe.db.delete("Parent App Device", {"user": user})
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


def check_strength(password, email):
    if len(password or "") < 8:
        frappe.throw(_("The password must have at least 8 characters."), title=_("Parent App"))
    from frappe.core.doctype.user.user import test_password_strength

    result = test_password_strength(password, user_data=(email,)) or {}
    feedback = result.get("feedback") or {}
    if cint(frappe.db.get_single_value("System Settings", "enable_password_policy")) and not feedback.get("password_policy_validation_passed", True):
        frappe.throw(_("The password is too weak. {0}").format(feedback.get("warning") or ""), title=_("Parent App"))


# ── core ─────────────────────────────────────────────────────────────────────
def enable_access(profile, password=None, send_email=False, login=None):
    """Create / update the app login of a Parent Profile. Returns what happened."""
    doc = profile if not isinstance(profile, str) else frappe.get_doc(DT, profile)
    login = (login or doc.get("app_login") or doc.email or "").strip().lower()
    if not login or not validate_email_address(login):
        frappe.throw(_("Parent {0} has no valid e-mail for the Parent App login.").format(doc.full_name or doc.name))
    result = {"parent": doc.name, "user": login, "created": False, "renamed": False,
              "password_generated": None, "password_changed": False, "emailed": False}

    current = doc.get("user")
    if current and current != login and frappe.db.exists("User", current) and not frappe.db.exists("User", login):
        frappe.rename_doc("User", current, login, force=True, show_alert=False)
        frappe.db.set_value("User", login, "email", login)
        result["renamed"] = True
    elif current and current != login and frappe.db.exists("User", current):
        disable_access(doc.name)  # moving to another existing account: retire the old one

    if frappe.db.exists("User", login):
        user = frappe.get_doc("User", login)
        if user.user_type == "System User":
            frappe.throw(_("{0} is a staff account and cannot be used as a parent login.").format(login))
        if not user.enabled:
            user.enabled = 1
            user.save(ignore_permissions=True)
    else:
        user = frappe.get_doc({
            "doctype": "User",
            "email": login,
            "first_name": (doc.first_name or login)[:140],
            "last_name": (doc.last_name or "")[:140],
            # User.mobile_no is unique in Frappe: copy it only when no other user has it
            "mobile_no": doc.mobile_no if doc.mobile_no and not frappe.db.exists("User", {"mobile_no": doc.mobile_no}) else None,
            "language": doc.preferred_language,
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
        rotate_api_secret(user.name)  # sign out the old mobile sessions
        result["password_changed"] = not result["password_generated"]

    frappe.db.set_value(DT, doc.name, {"app_access": 1, "app_login": user.name, "user": user.name}, update_modified=False)
    doc.user = user.name
    if send_email:
        result["emailed"] = _send_credentials(doc, user.name, password)
    return result


def rotate_api_secret(user):
    if frappe.db.get_value("User", user, "api_key"):
        from frappe.utils.password import set_encrypted_password

        set_encrypted_password("User", user, frappe.generate_hash(length=15), "api_secret")


def _send_credentials(doc, user, password):
    app = frappe.db.get_single_value("Nursery Settings", "facility_name") or _("Baby Care")
    lines = [
        _("Hello {0},").format(escape_html(doc.full_name or "")),
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
    for row in doc.get("parents") or []:
        info = frappe.db.get_value(DT, row.parent_profile, ["name", "email", "app_access", "app_login", "user", "is_active"], as_dict=True)
        if not info or info.user or not cint(info.is_active):
            continue
        if not cint(info.app_access) and info.app_login:
            continue  # access was switched off on purpose
        email = (info.email or "").strip().lower()
        if not email or not validate_email_address(email):
            continue
        if frappe.db.get_value("User", email, "user_type") == "System User":
            continue
        if frappe.db.get_value(DT, {"user": email, "name": ("!=", info.name)}):
            continue
        try:
            _report(enable_access(info.name, login=email))
        except Exception:
            frappe.log_error(title=f"Baby Care: automatic parent login failed for {info.name}")


# ── staff API (Parent Profile form button) ───────────────────────────────────
@frappe.whitelist(methods=["POST"])
def reset_parent_password(parent_profile, password=None, send_email=0):
    """Set a new password (or generate one) for the parent's app login."""
    frappe.has_permission(DT, "write", parent_profile, throw=True)
    doc = frappe.get_doc(DT, parent_profile)
    if not cint(doc.app_access) or not doc.user:
        frappe.throw(_("Enable Parent App access for this parent first."))
    generated = None
    if not password:
        password = generated = generate_password()
    check_strength(password, doc.user)
    from frappe.utils.password import update_password

    update_password(doc.user, password)
    rotate_api_secret(doc.user)
    emailed = _send_credentials(doc, doc.user, password) if cint(send_email) else False
    return {"user": doc.user, "password": generated, "emailed": emailed}
