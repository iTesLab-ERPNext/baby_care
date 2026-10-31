import frappe


def boot_session(bootinfo):
    """Inject nursery settings into boot so client JS can read them."""
    if frappe.session.user == "Guest":
        return
    try:
        settings = frappe.get_single("Nursery Settings")
        bootinfo.nursery_settings = {
            "facility_name": settings.facility_name,
            "facility_type": settings.facility_type,
            "allow_partial_payment": settings.allow_partial_payment,
            "enforce_class_capacity": settings.enforce_class_capacity,
        }
    except Exception:
        bootinfo.nursery_settings = {}

    # Navbar "Baby Care" menu (same sections as the workspace, filtered by permissions)
    try:
        from baby_care.baby_care_management.api.navigation import get_menu

        bootinfo.baby_care_menu = get_menu()
    except Exception:
        frappe.log_error(title="Baby Care: navbar menu could not be built")
        bootinfo.baby_care_menu = None
