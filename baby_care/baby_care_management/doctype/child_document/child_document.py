import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today


class ChildDocument(Document):
    def validate(self):
        self._check_expiry()

    def _check_expiry(self):
        if self.expiry_date and getdate(self.expiry_date) < getdate(today()):
            self.status = "Expired"
