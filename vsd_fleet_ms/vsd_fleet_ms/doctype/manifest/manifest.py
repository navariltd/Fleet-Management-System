# Copyright (c) 2023, VV SYSTEMS DEVELOPER LTD and contributors
# For license information, please see license.txt

import datetime
import re
import frappe
import json

from frappe.model.document import Document


class Manifest(Document):
    def onload(self):
        if self.name and self.docstatus == 0:
            self.update_cargo_registration_details()
            self.update_trips()
            self.validate_has_trailers()

    def validate(self):
        if (
            self.transporter_type == "In House"
            and self.truck
            and self.docstatus == 1
            and self.vehicle_trip
        ):
            truck = frappe.get_doc("Truck", self.truck)
            truck.status = "On Trip"
            truck.trans_ms_current_trip = self.vehicle_trip
            truck.save()

    def before_save(self):
        self.assign_missing_manifest_cargo_ids()
        self.validate_transporter_type()
        self.validate_has_trailers()
        self.sync_manifest_customer_to_child_rows()

        if self.name:
            self.update_cargo_registration_details()
            self.update_trips()

    def assign_missing_manifest_cargo_ids(self):
        for row in self.manifest_cargo_details or []:
            if not row.cargo_id:
                row.cargo_id = self.generate_manifest_cargo_id(row.cargo_type)

    def sync_manifest_customer_to_child_rows(self):
        if not self.customer:
            return
        for row in self.manifest_cargo_details or []:
            if not row.customer_name:
                row.customer_name = self.customer

    def generate_manifest_cargo_id(self, cargo_type):
        safe_cargo_type = (cargo_type or "CARGO").strip().replace("/", "-")
        date_part = datetime.datetime.now().strftime("%d/%m/%Y")
        prefix = f"{safe_cargo_type}-{date_part}-"

        existing_rows = frappe.get_all(
            "Manifest Cargo Details",
            filters={"cargo_id": ["like", f"{prefix}%"]},
            fields=["cargo_id"],
            limit_page_length=0,
        )

        max_suffix = 0
        for existing in existing_rows:
            value = existing.get("cargo_id") or ""
            match = re.search(r"-(\d{4})$", value)
            if match:
                max_suffix = max(max_suffix, int(match.group(1)))

        return f"{prefix}{max_suffix + 1:04d}"

    def on_submit(self):
        self.set_truck_dimension()

    def cargo_allocation(self):
        if self.transporter_type == "Sub-Contractor":
            for row in self.manifest_cargo_details:
                row.specific_cargo_allocated = ""
        elif self.transporter_type == "In House":
            for row in self.manifest_cargo_details:
                row.sub_contractor_cargo_allocation = ""

    def update_trips(self):
        trips = frappe.get_all("Trips", filters={"manifest": self.name, "docstatus": 0})
        for trip in trips:
            trip_doc = frappe.get_doc("Trips", trip.name)
            if self.transporter_type == "Sub-Contractor":
                trip_doc.transporter_type = "Sub-Contractor"
                trip_doc.sub_contactor_truck_license_plate_no = (
                    self.sub_contactor_truck_license_plate_no
                )
                trip_doc.sub_contactor_driver_name = self.sub_contactor_driver_name
                trip_doc.truck_number = ""
                trip_doc.assigned_driver = ""
                trip_doc.driver_name = ""
                trip_doc.trailer_1 = ""
                trip_doc.sub_contactor_trailer_1 = self.sub_contactor_trailer_1
                trip_doc.trailer_2 = ""
                trip_doc.sub_contactor_trailer_2 = self.sub_contactor_trailer_2
                trip_doc.trailer_3 = ""
                trip_doc.sub_contactor_trailer_3 = self.sub_contactor_trailer_3

            elif self.transporter_type == "In House":
                trip_doc.transporter_type = "In House"
                trip_doc.sub_contactor_truck_license_plate_no = ""
                trip_doc.sub_contactor_driver_name = ""
                trip_doc.truck_number = self.truck_license_plate_no
                trip_doc.assigned_driver = self.driver_name
                trip_doc.trailer_1 = self.trailer_1
                trip_doc.sub_contactor_trailer_1 = ""
                trip_doc.trailer_2 = self.trailer_2
                trip_doc.sub_contactor_trailer_2 = ""
                trip_doc.trailer_3 = self.trailer_3
                trip_doc.sub_contactor_trailer_3 = ""
            trip_doc.save()

    def update_cargo_registration_details(self):
        cargo_details = frappe.get_all(
            "Cargo Detail", filters={"manifest_number": self.name, "docstatus": 0}
        )
        for cargo in cargo_details:
            cargo_detail = frappe.get_doc("Cargo Detail", cargo.name)
            if self.transporter_type == "Sub-Contractor":
                cargo_detail.transporter_type = "Sub-Contractor"
                cargo_detail.assigned_truck = ""
                cargo_detail.assigned_driver = ""
                cargo_detail.truck_number = self.sub_contactor_truck_license_plate_no
                cargo_detail.driver_name = self.sub_contactor_driver_name
            elif self.transporter_type == "In House":
                cargo_detail.transporter_type = "In House"
                cargo_detail.assigned_truck = self.truck_license_plate_no
                cargo_detail.assigned_driver = self.driver_name
                cargo_detail.truck_number = ""
                cargo_detail.driver_name = ""

            # Save the parent Cargo Registration document to persist changes
            cargo_registration = frappe.get_doc(
                "Cargo Registration", cargo_detail.parent
            )
            cargo_registration.save()

    def validate_has_trailers(self):
        if self.has_trailers == 0:
            self.trailer_1 = ""
            self.sub_contactor_trailer_1 = ""
            self.trailer1_type = ""
            self.trailer_2 = ""
            self.sub_contactor_trailer_2 = ""
            self.trailer2_type = ""
            self.trailer_3 = ""
            self.sub_contactor_trailer_3 = ""
            self.trailer3_type = ""
            if self.transporter_type == "Sub-Contractor":
                for row in self.manifest_cargo_details:
                    row.cargo_allocation = "Truck"
                    row.sub_contractor_cargo_allocation = (
                        self.sub_contactor_truck_license_plate_no
                    )
                    row.specific_cargo_allocated = ""

            elif self.transporter_type == "In House":
                for row in self.manifest_cargo_details:
                    row.cargo_allocation = "Truck"
                    row.specific_cargo_allocated = self.truck if self.truck else ""
                    row.sub_contractor_cargo_allocation = ""

    def validate_transporter_type(self):
        if self.transporter_type == "In House":
            self.sub_contactor_truck_license_plate_no = ""
            self.sub_contactor_driver_name = ""
            self.sub_contactor_trailer_1 = ""
            self.sub_contactor_trailer_2 = ""
            self.sub_contactor_trailer_3 = ""

        elif self.transporter_type == "Sub-Contractor":
            self.truck = ""
            self.assigned_driver = ""
            self.driver_name = ""
            self.truck = ""
            self.trailer_1 = ""
            self.trailer1_type = ""
            self.trailer_2 = ""
            self.trailer2_type = ""
            self.trailer_3 = ""
            self.trailer3_type = ""

    def set_truck_dimension(self):
        # Check if truck is settled as accounting dimension on transport settings
        tr_settings = frappe.get_doc("Transport Settings")
        has_si_truck_dimension = None
        has_sii_truck_dimension = None
        for d in tr_settings.accounting_dimension:
            if (
                not has_si_truck_dimension
                and d.get("dimension_name") == "Truck"
                and d.get("target_doctype") == "Sales Invoice"
            ):
                has_si_truck_dimension = True

            if (
                not has_sii_truck_dimension
                and d.get("dimension_name") == "Truck"
                and d.get("target_doctype") == "Sales Invoice Item"
            ):
                has_sii_truck_dimension = True

        if not has_si_truck_dimension and not has_sii_truck_dimension:
            return

        # Set truck dimension on sales invoice and sales invoice item
        for row in self.manifest_cargo_details:
            invoice_id = frappe.db.get_value("Cargo Detail", row.cargo_id, "invoice")
            invoice_doc = frappe.get_doc("Sales Invoice", invoice_id)

            # if has_si_truck_dimension and not invoice_doc.truck:
            # 	invoice_doc.truck = self.truck

            if has_sii_truck_dimension:
                for d in invoice_doc.items:
                    if row.cargo_id == d.cargo_id:
                        d.truck = self.truck

            invoice_doc.save(ignore_permissions=True)


@frappe.whitelist()
def get_manifests(filter):
    # Implement the logic to fetch the manifests to be billed based on the provided filters

    # frappe.msgprint(str(filters))
    manifests = frappe.get_all(
        "Manifest",
        filters=filter,
        fields=[
            "name",
            "route",
            "truck",
            "driver_name",
        ],  # Adjust the fields as per your requirements
    )

    return manifests


@frappe.whitelist()
def create_manifest_from_cargo_registration(args_array):
    pass


@frappe.whitelist()
def create_cargo_registration_from_manifest(manifest_name):
    manifest = frappe.get_doc("Manifest", manifest_name)

    if manifest.docstatus != 1:
        frappe.throw("Cargo Registration can only be created from a submitted Manifest.")

    default_cargo_route = manifest.route or None

    if manifest.cargo_registration:
        frappe.throw("This Manifest already has a linked Cargo Registration.")

    if not manifest.customer:
        frappe.throw("Please set Customer on the Manifest before creating Cargo Registration.")

    if not manifest.manifest_cargo_details:
        frappe.throw("Please add at least one cargo row on the Manifest.")

    cargo_registration = frappe.new_doc("Cargo Registration")
    cargo_registration.customer = manifest.customer
    cargo_registration.posting_date = manifest.posting_date or datetime.date.today()

    company = frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default(
        "company"
    )
    if company:
        cargo_registration.company = company

    for row in manifest.manifest_cargo_details:
        missing_fields = []
        if not row.cargo_route and not default_cargo_route:
            missing_fields.append("cargo_route")
        if not row.number_of_package:
            missing_fields.append("number_of_package")
        if not row.weight:
            missing_fields.append("weight")
        if not row.cargo_location_country:
            missing_fields.append("cargo_location_country")
        if not row.cargo_loading_city:
            missing_fields.append("cargo_loading_city")
        if not row.cargo_destination_country:
            missing_fields.append("cargo_destination_country")
        if not row.cargo_destination_city:
            missing_fields.append("cargo_destination_city")
        if not row.expected_loading_date:
            missing_fields.append("expected_loading_date")
        if not row.expected_offloading_date:
            missing_fields.append("expected_offloading_date")

        if missing_fields:
            frappe.throw(
                f"Manifest Cargo Details row {row.idx} is missing required values: "
                f"{', '.join(missing_fields)}"
            )

        cargo_registration.append(
            "cargo_details",
            {
                "cargo_id": row.cargo_id,
                "cargo_type": row.cargo_type,
                "container_size": row.container_size or "Loose",
                "seal_number": row.seal_number,
                "bl_number": row.bl_number,
                "cargo_route": row.cargo_route or default_cargo_route,
                "net_weight": row.weight,
                "number_of_packages": row.number_of_package,
                "container_number": row.container_number,
                "service_item": "Transportation Service",
                "currency": frappe.defaults.get_user_default("Currency") or "USD",
                "rate": getattr(row, "rate", 0) or 0,
                "cargo_location_country": row.cargo_location_country,
                "cargo_location_city": row.cargo_loading_city,
                "loading_date": row.expected_loading_date,
                "cargo_destination_country": row.cargo_destination_country,
                "cargo_destination_city": row.cargo_destination_city,
                "expected_offloading_date": row.expected_offloading_date,
                "manifest_number": manifest.name,
            },
        )

    cargo_registration.insert(ignore_permissions=True)
    manifest.db_set("cargo_registration", cargo_registration.name, update_modified=False)

    return cargo_registration.as_dict()


@frappe.whitelist()
def add_to_existing_manifest(args_array):
    args_dict = json.loads(args_array)
    manifest = frappe.get_doc("Manifest", args_dict.get("manifest"))
    manifest.cargo_registration = args_dict.get("parent_doctype_name")
    manifest.append(
        "manifest_cargo_details",
        {
            "cargo_id": args_dict.get("cargo_id"),
            "cargo_route": args_dict.get("cargo_route"),
            "cargo_type": args_dict.get("cargo_type"),
            "number_of_package": args_dict.get("number_of_package"),
            "weight": args_dict.get("weight"),
            "bl_number": args_dict.get("bl_number"),
            "expected_loading_date": args_dict.get("expected_loading_date"),
            "expected_offloading_date": args_dict.get("expected_offloading_date"),
            "customer_name": args_dict.get("customer_name"),
            "cargo_destination_country": args_dict.get("cargo_destination_country"),
            "cargo_destination_city": args_dict.get("cargo_destination_city"),
            "container_size": args_dict.get("container_size"),
            "seal_number": args_dict.get("seal_number"),
            "container_number": args_dict.get("container_number"),
            "cargo_loading_city": args_dict.get("cargo_loading_city"),
            "cargo_location_country": args_dict.get("cargo_location_country"),
        },
    )
    if manifest.save():
        cargo_registration = frappe.get_doc(
            "Cargo Registration", args_dict.get("parent_doctype_name")
        )
        if cargo_registration:
            for row in cargo_registration.cargo_details:
                if row.name == args_dict.get("cargo_id"):
                    row.manifest_number = args_dict.get("manifest")
                    # Populate assigned_truck based on transporter type
                    if manifest.transporter_type == "In House":
                        row.assigned_truck = manifest.truck_license_plate_no
                        row.assigned_driver = manifest.driver_name
                    elif manifest.transporter_type == "Sub-Contractor":
                        row.truck_number = manifest.sub_contactor_truck_license_plate_no
                        row.driver_name = manifest.sub_contactor_driver_name
                    cargo_registration.save()
                    break
    return manifest.as_dict()


@frappe.whitelist()
def create_new_manifest(args_array):
    args_dict = json.loads(args_array)
    manifest = frappe.new_doc("Manifest")
    manifest.route = args_dict.get("cargo_route")
    manifest.cargo_registration = args_dict.get("parent_doctype_name")
    manifest.posting_date = datetime.datetime.now().date()
    manifest.append(
        "manifest_cargo_details",
        {
            "cargo_id": args_dict.get("cargo_id"),
            "cargo_route": args_dict.get("cargo_route"),
            "cargo_type": args_dict.get("cargo_type"),
            "number_of_package": args_dict.get("number_of_package"),
            "weight": args_dict.get("weight"),
            "bl_number": args_dict.get("bl_number"),
            "expected_loading_date": args_dict.get("expected_loading_date"),
            "expected_offloading_date": args_dict.get("expected_offloading_date"),
            "customer_name": args_dict.get("customer_name"),
            "cargo_destination_country": args_dict.get("cargo_destination_country"),
            "cargo_destination_city": args_dict.get("cargo_destination_city"),
            "container_size": args_dict.get("container_size"),
            "seal_number": args_dict.get("seal_number"),
            "container_number": args_dict.get("container_number"),
            "cargo_loading_city": args_dict.get("cargo_loading_city"),
            "cargo_location_country": args_dict.get("cargo_location_country"),
        },
    )
    manifest.save()
    if manifest.name:
        cargo_registration = frappe.get_doc(
            "Cargo Registration", args_dict.get("parent_doctype_name")
        )
        if cargo_registration:
            for row in cargo_registration.cargo_details:
                if row.name == args_dict.get("cargo_id"):
                    row.manifest_number = manifest.name
                    cargo_registration.save()
                    break

    return manifest.as_dict()
