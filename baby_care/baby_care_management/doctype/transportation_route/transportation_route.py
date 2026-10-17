import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class TransportationRoute(Document):
    def validate(self):
        if flt(self.monthly_fee) < 0:
            frappe.throw(_("Monthly fee cannot be negative."))
        names = [s.stop_name for s in self.stops or []]
        if len(names) != len(set(names)):
            frappe.throw(_("Stop names must be unique on a route."))
