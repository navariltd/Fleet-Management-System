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
            doctype_doc = frappe.get_doc("DocType", "Transport Settings")

            if doctype_doc.module != "VSD Fleet MS":
                frappe.logger().info(
                    f"Updating Transport Settings module from '{doctype_doc.module}' to 'VSD Fleet MS'"
                )
                doctype_doc.module = "VSD Fleet MS"
                doctype_doc.save(ignore_permissions=True)
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
