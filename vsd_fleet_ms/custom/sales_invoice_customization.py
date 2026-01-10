# Copyright (c) 2025, VV SYSTEMS DEVELOPER LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import nowdate


@frappe.whitelist()
def get_uninvoiced_cargo_details(customer, company=None):
    """
    Fetch all uninvoiced cargo details for a specific customer.

    Args:
        customer: Customer name
        company: Company name (optional)

    Returns:
        List of cargo details that haven't been invoiced yet
    """
    if not customer:
        frappe.throw(_("Please select a Customer first"))

    filters = {
        "docstatus": 1,  # Only submitted cargo registrations
        "customer": customer,
    }

    if company:
        filters["company"] = company

    # Get all cargo registrations for this customer
    cargo_registrations = frappe.get_all(
        "Cargo Registration", filters=filters, fields=["name"]
    )

    if not cargo_registrations:
        frappe.msgprint(
            _("No Cargo Registrations found for customer {0}").format(customer)
        )
        return []

    # Get all cargo details from these registrations that haven't been invoiced
    cargo_details = []

    for cargo_reg in cargo_registrations:
        details = frappe.get_all(
            "Cargo Detail",
            filters={
                "parent": cargo_reg.name,
                "parenttype": "Cargo Registration",
                "docstatus": 1,
                "invoice": ["in", ["", None]],  # Not yet invoiced
            },
            fields=[
                "name",
                "parent",
                "service_item",
                "rate",
                "currency",
                "cargo_route",
                "cargo_type",
                "net_weight",
                "number_of_packages",
                "manifest_number",
                "transporter_type",
                "assigned_truck",
                "truck_number",
                "driver_name",
                "created_trip",
                "cargo_destination_city",
                "cargo_destination_country",
            ],
        )
        cargo_details.extend(details)

    # Calculate weight in tonnes and enrich with manifest/truck details
    for detail in cargo_details:
        # Convert net_weight from kg to tonnes
        if detail.get("net_weight"):
            detail["net_weight_tonne"] = detail["net_weight"] / 1000
        else:
            detail["net_weight_tonne"] = 0
        if detail.get("manifest_number"):
            manifest = frappe.get_doc("Manifest", detail["manifest_number"])
            if manifest.transporter_type == "In House":
                detail["truck_from_manifest"] = manifest.truck
                detail["truck_license_plate"] = manifest.truck_license_plate_no
                detail["driver_from_manifest"] = manifest.driver_name
            elif manifest.transporter_type == "Sub-Contractor":
                detail["truck_license_plate"] = (
                    manifest.sub_contactor_truck_license_plate_no
                )
                detail["driver_from_manifest"] = manifest.sub_contactor_driver_name

    return cargo_details


@frappe.whitelist()
def create_sales_invoice_from_cargo_details(customer, company, cargo_detail_ids):
    """
    Create a Sales Invoice from selected cargo details.

    Args:
        customer: Customer name
        company: Company name
        cargo_detail_ids: JSON string of cargo detail IDs

    Returns:
        Sales Invoice document dict
    """
    import json

    if isinstance(cargo_detail_ids, str):
        cargo_detail_ids = json.loads(cargo_detail_ids)

    if not cargo_detail_ids:
        frappe.throw(_("Please select at least one Cargo Detail"))

    # Fetch cargo details
    cargo_details = frappe.get_all(
        "Cargo Detail",
        filters={
            "name": ["in", cargo_detail_ids],
            "docstatus": 1,
            "invoice": ["in", ["", None]],
        },
        fields=[
            "name",
            "parent",
            "service_item",
            "rate",
            "currency",
            "cargo_route",
            "net_weight",
            "manifest_number",
            "transporter_type",
            "assigned_truck",
            "truck_number",
            "driver_name",
            "created_trip",
        ],
    )

    if not cargo_details:
        frappe.throw(
            _("No eligible Cargo Details found. They may have already been invoiced.")
        )

    # Create Sales Invoice
    invoice = frappe.get_doc(
        {
            "doctype": "Sales Invoice",
            "customer": customer,
            "company": company,
            "posting_date": nowdate(),
            "items": [],
        }
    )

    # Add items to invoice
    for detail in cargo_details:
        description = build_item_description(detail)

        # Get currency from first cargo detail
        if not invoice.currency and detail.get("currency"):
            invoice.currency = detail["currency"]

        # Convert net_weight from kg to tonnes
        net_weight_tonne = detail.get("net_weight", 1000) / 1000

        # Check if allow_bill_on_weight custom field exists
        allow_bill_on_weight = (
            frappe.db.get_value("Cargo Detail", detail["name"], "allow_bill_on_weight")
            if frappe.db.has_column("Cargo Detail", "allow_bill_on_weight")
            else 0
        )

        # Get bill_uom if it exists
        bill_uom = (
            frappe.db.get_value("Cargo Detail", detail["name"], "bill_uom")
            if frappe.db.has_column("Cargo Detail", "bill_uom")
            else "Nos"
        )

        # Determine quantity based on billing preference
        qty = net_weight_tonne if allow_bill_on_weight else 1
        uom = bill_uom or "Nos"

        # Prepare item dictionary
        item_dict = {
            "item_code": detail["service_item"],
            "qty": qty,
            "uom": uom,
            "rate": detail.get("rate", 0),
            "description": description,
            "cargo_id": detail["name"],
        }

        # Add truck field if assigned_truck exists and truck field is available
        if detail.get("assigned_truck"):
            if frappe.db.has_column("Sales Invoice Item", "truck"):
                item_dict["truck"] = detail["assigned_truck"]

        invoice.append("items", item_dict)

    # Set missing values and calculate totals
    invoice.set_missing_values()
    invoice.calculate_taxes_and_totals()

    # Save the invoice (don't submit automatically)
    invoice.insert(ignore_permissions=True)

    # Update cargo details with invoice reference
    for detail in cargo_details:
        frappe.db.set_value("Cargo Detail", detail["name"], "invoice", invoice.name)

    frappe.db.commit()

    frappe.msgprint(
        _("Sales Invoice {0} created successfully").format(invoice.name), alert=True
    )

    return invoice.as_dict()


def build_item_description(cargo_detail):
    """
    Build a comprehensive description for the invoice item including truck details.

    Args:
        cargo_detail: Cargo Detail document dict

    Returns:
        HTML formatted description string
    """
    description = ""

    # Add truck/vehicle details
    if cargo_detail.get("transporter_type") == "In House":
        if cargo_detail.get("assigned_truck"):
            truck_number = cargo_detail.get("assigned_truck")
            description += f"<b>VEHICLE NUMBER:</b> {truck_number}"
        if cargo_detail.get("created_trip"):
            description += f"<br><b>TRIP:</b> {cargo_detail['created_trip']}"
    elif cargo_detail.get("transporter_type") == "Sub-Contractor":
        if cargo_detail.get("truck_number"):
            description += f"<b>VEHICLE NUMBER:</b> {cargo_detail['truck_number']}"
        if cargo_detail.get("driver_name"):
            description += f"<br><b>DRIVER NAME:</b> {cargo_detail['driver_name']}"

    # Fetch details from Manifest if available
    if cargo_detail.get("manifest_number"):
        try:
            manifest = frappe.get_doc("Manifest", cargo_detail["manifest_number"])
            if (
                manifest.transporter_type == "In House"
                and manifest.truck_license_plate_no
            ):
                if not description:
                    description += (
                        f"<b>VEHICLE NUMBER:</b> {manifest.truck_license_plate_no}"
                    )
                description += f"<br><b>DRIVER:</b> {manifest.driver_name or 'N/A'}"
            elif manifest.transporter_type == "Sub-Contractor":
                if not description:
                    description += f"<b>VEHICLE NUMBER:</b> {manifest.sub_contactor_truck_license_plate_no}"
                    description += (
                        f"<br><b>DRIVER NAME:</b> {manifest.sub_contactor_driver_name}"
                    )
        except Exception as e:
            frappe.log_error(f"Error fetching manifest: {str(e)}")

    # Add route details
    if cargo_detail.get("cargo_route"):
        description += f"<br><b>ROUTE:</b> {cargo_detail['cargo_route']}"

    return description


@frappe.whitelist()
def update_cargo_detail_on_invoice_cancel(doc, method=None):
    """
    Clear invoice reference from cargo details when invoice is cancelled.

    Args:
        doc: Sales Invoice document
        method: (optional) method name
    """
    cargo_details = frappe.get_all(
        "Cargo Detail", filters={"invoice": doc.name}, fields=["name"]
    )

    for detail in cargo_details:
        frappe.db.set_value("Cargo Detail", detail["name"], "invoice", "")

    frappe.db.commit()
