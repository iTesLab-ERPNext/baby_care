import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, getdate


class ChildTransportation(Document):
    def validate(self):
        if not cint(frappe.db.get_single_value("Nursery Settings", "enable_transportation")):
            frappe.throw(_("Transportation is disabled in Nursery Settings."))
        if self.start_date and self.end_date and getdate(self.end_date) < getdate(self.start_date):
            frappe.throw(_("End date cannot be before start date."))
        route = frappe.get_doc("Transportation Route", self.route)
        if not route.is_active:
            frappe.throw(_("Route {0} is inactive.").format(self.route))
        stops = {s.stop_name for s in route.stops}
        for fn in ("pickup_stop", "dropoff_stop"):
            if self.get(fn) and stops and self.get(fn) not in stops:
                frappe.throw(_("{0} is not a stop on route {1}.").format(self.get(fn), self.route))
        if self.is_active and cint(route.capacity):
            used = frappe.db.count("Child Transportation", {"route": self.route, "is_active": 1, "name": ("!=", self.name)})
            if used >= cint(route.capacity):
                frappe.throw(_("Route {0} is full ({1}/{2}).").format(self.route, used, route.capacity))
        dup = frappe.db.get_value("Child Transportation", {"child": self.child, "is_active": 1, "name": ("!=", self.name)}, "name")
        if self.is_active and dup:
            frappe.throw(_("{0} already has active transportation {1}.").format(self.child, dup))
