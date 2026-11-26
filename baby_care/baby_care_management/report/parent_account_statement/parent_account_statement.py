import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = [
        {"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 100},
        {"label": _("Type"), "fieldname": "voucher_type", "fieldtype": "Data", "width": 120},
        {"label": _("Reference"), "fieldname": "voucher_no", "fieldtype": "Dynamic Link", "options": "voucher_type", "width": 160},
        {"label": _("Child"), "fieldname": "child", "fieldtype": "Link", "options": "Child", "width": 120},
        {"label": _("Description"), "fieldname": "description", "fieldtype": "Data", "width": 220},
        {"label": _("Debit (Invoiced)"), "fieldname": "debit", "fieldtype": "Currency", "width": 130},
        {"label": _("Credit (Paid)"), "fieldname": "credit", "fieldtype": "Currency", "width": 130},
        {"label": _("Balance"), "fieldname": "balance", "fieldtype": "Currency", "width": 130},
    ]
    if not filters.get("parent_profile"):
        return columns, [], _("Select a parent to see the statement.")
    from baby_care.baby_care_management.utils.billing import get_parent_statement

    st = get_parent_statement(filters.parent_profile)
    entries = []
    for i in st["invoices"]:
        if filters.get("from_date") and str(i.posting_date) < str(filters.from_date):
            continue
        entries.append({"date": i.posting_date, "voucher_type": "Nursery Invoice", "voucher_no": i.name, "child": i.child,
                        "description": _("Invoice {0} (due {1})").format(i.billing_period or "", i.due_date), "debit": flt(i.grand_total), "credit": 0})
    for p in st["payments"]:
        if filters.get("from_date") and str(p.payment_date) < str(filters.from_date):
            continue
        entries.append({"date": p.payment_date, "voucher_type": "Nursery Payment", "voucher_no": p.name, "child": None,
                        "description": _("Payment {0}").format(_(p.mode_of_payment or "")) + (f" — {p.reference_no}" if p.reference_no else ""), "debit": 0, "credit": flt(p.amount)})
    entries.sort(key=lambda e: (str(e["date"]), e["voucher_type"] != "Nursery Invoice"))
    bal = 0
    for e in entries:
        bal += e["debit"] - e["credit"]
        e["balance"] = bal
    summary = [
        {"label": _("Children"), "value": len(st["children"]), "indicator": "Blue"},
        {"label": _("Open subscriptions"), "value": len([s for s in st["subscriptions"] if s.status in ("Active", "Pending", "Suspended")]), "indicator": "Green"},
        {"label": _("Outstanding"), "value": st["outstanding"], "datatype": "Currency", "indicator": "Red"},
        {"label": _("Credit"), "value": st["credit"], "datatype": "Currency", "indicator": "Green"},
        {"label": _("Next due date"), "value": str(st["next_due"] or "-"), "indicator": "Orange"},
    ]
    return columns, entries, None, None, summary
