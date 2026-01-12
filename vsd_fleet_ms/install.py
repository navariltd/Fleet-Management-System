import frappe


def after_migrate():
    """
    Hook that runs after migrate to ensure Transport Settings doctype
    has the correct module field value.
    """
    ensure_transport_settings_module()


def ensure_transport_settings_module():
    """
    Ensure the Transport Settings doctype's module field is set to "VSD Fleet MS"
    """
    try:
        if frappe.db.exists("DocType", "Transport Settings"):
            current_module = frappe.db.get_value(
                "DocType", "Transport Settings", "module"
            )

            if current_module != "VSD Fleet MS":
                frappe.logger().info(
                    f"Updating Transport Settings module from '{current_module}' to 'VSD Fleet MS'"
                )
                frappe.db.set_value(
                    "DocType",
                    "Transport Settings",
                    "module",
                    "VSD Fleet MS",
                    update_modified=False,
                )
                frappe.db.commit()
                frappe.logger().info("Transport Settings module updated successfully")
            else:
                frappe.logger().info(
                    "Transport Settings module is already set to 'VSD Fleet MS'"
                )
    except Exception as e:
        frappe.log_error(
            message=f"Error updating Transport Settings module: {str(e)}",
            title="Transport Settings Module Update Error",
        )
