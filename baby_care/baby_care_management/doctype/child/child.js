frappe.ui.form.on("Child", {
    refresh(frm) {
        if (!frm.doc.__islocal) {
            frm.add_custom_button(__("Medical Record"), function () {
                frappe.set_route("List", "Medical Record", {"child": frm.doc.name});
            }, __("View"));

            frm.add_custom_button(__("Attendance"), function () {
                frappe.set_route("List", "Child Attendance", {"child": frm.doc.name});
            }, __("View"));

            frm.add_custom_button(__("Documents"), function () {
                frappe.set_route("List", "Child Document", {"child": frm.doc.name});
            }, __("View"));

            frm.add_custom_button(__("Create Subscription"), function () {
                frappe.new_doc("Child Subscription", {
                    child: frm.doc.name,
                    parent_customer: frm.doc.parents && frm.doc.parents[0]
                        ? frm.doc.parents[0].parent_customer : ""
                });
            }, __("Actions"));

            frm.add_custom_button(__("Record Attendance"), function () {
                frappe.new_doc("Child Attendance", {child: frm.doc.name});
            }, __("Actions"));
        }

        // Status indicator colour
        const color_map = {
            "Active": "green", "Pending": "orange",
            "Suspended": "red", "Withdrawn": "grey", "Graduated": "blue"
        };
        frm.set_indicator_formatter("enrollment_status", function(doc) {
            return color_map[doc.enrollment_status] || "grey";
        });
    },

    first_name(frm) { _set_full_name(frm); },
    last_name(frm) { _set_full_name(frm); }
});

function _set_full_name(frm) {
    frm.set_value(
        "full_name",
        ((frm.doc.first_name || "") + " " + (frm.doc.last_name || "")).trim()
    );
}
