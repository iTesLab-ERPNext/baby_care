// Baby Care — Customer (Parent) profile extension
frappe.ui.form.on("Customer", {
    refresh(frm) {
        if (frm.doc.__islocal) return;

        frm.add_custom_button(__("Children"), function () {
            frappe.route_options = {};
            frappe.set_route("List", "Child", {
                "parents.parent_customer": frm.doc.name
            });
        }, __("Baby Care"));

        frm.add_custom_button(__("Subscriptions"), function () {
            frappe.set_route("List", "Child Subscription", {
                "parent_customer": frm.doc.name
            });
        }, __("Baby Care"));

        frm.add_custom_button(__("Account Statement"), function () {
            frappe.set_route("query-report/General Ledger", {
                "party_type": "Customer",
                "party": frm.doc.name
            });
        }, __("Baby Care"));

        // Summary card
        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Child",
                filters: [["Child Parent Link", "parent_customer", "=", frm.doc.name]],
                fields: ["full_name", "enrollment_status", "subscription_status"],
                limit: 20
            },
            callback(r) {
                if (!r.message || !r.message.length) return;
                let html = `<div class="bc-parent-children">
                    <h6>${__("Enrolled Children")}</h6>
                    <table class="table table-sm table-bordered">
                      <thead><tr>
                        <th>${__("Child")}</th>
                        <th>${__("Enrollment")}</th>
                        <th>${__("Subscription")}</th>
                      </tr></thead><tbody>`;
                r.message.forEach(c => {
                    html += `<tr>
                        <td><a href="/app/child/${encodeURIComponent(c.full_name)}">${c.full_name}</a></td>
                        <td>${c.enrollment_status || ""}</td>
                        <td>${c.subscription_status || ""}</td>
                    </tr>`;
                });
                html += "</tbody></table></div>";
                frm.dashboard.add_section(html, __("Baby Care"));
                frm.dashboard.show();
            }
        });
    }
});
