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
