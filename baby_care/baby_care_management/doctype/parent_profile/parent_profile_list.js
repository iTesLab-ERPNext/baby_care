frappe.listview_settings["Parent Profile"] = {
	add_fields: ["is_active", "app_access"],
	get_indicator(doc) {
		if (!doc.is_active) return [__("Inactive"), "gray", "is_active,=,0"];
		return doc.app_access ? [__("App enabled"), "green", "app_access,=,1"] : [__("Active"), "blue", "is_active,=,1"];
	},
};
