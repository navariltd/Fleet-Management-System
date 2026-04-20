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
        if self.name:
            self.update_cargo_registration_details()
            self.update_trips()

    def assign_missing_manifest_cargo_ids(self):
        for row in self.manifest_cargo_details or []:
            if not row.cargo_id:
                row.cargo_id = self.generate_manifest_cargo_id(row.cargo_type)

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
        self.create_cargo_registration_on_submit()
        self.set_truck_dimension()

    def create_cargo_registration_on_submit(self):
        if not self.manifest_cargo_details:
            return

        valid_rows = [d for d in self.manifest_cargo_details if d.cargo_id]
        if not valid_rows:
            frappe.throw("At least one Manifest Cargo Details row must have a Cargo ID.")

        source_rows = self.get_source_cargo_details()
        first_source_row = next(iter(source_rows.values()), {}) if source_rows else {}

        customers = set()
        for row in valid_rows:
            source = source_rows.get(row.cargo_id)
            customers.add((row.customer_name or (source or {}).get("parent_customer") or "").strip())
        customers.discard("")

        if len(customers) > 1:
            frappe.throw(
                "Manifest contains cargo from multiple customers. "
                "Submit separate manifests per customer to auto-create Cargo Registration."
            )

        customer = next(iter(customers), None) or first_source_row.get("parent_customer")
        if not customer:
            frappe.throw(
                "Customer is required to create Cargo Registration from submitted Manifest."
            )

        cargo_registration = frappe.new_doc("Cargo Registration")
        cargo_registration.customer = customer
        cargo_registration.posting_date = self.posting_date or datetime.date.today()
        company = first_source_row.get("parent_company") or frappe.defaults.get_global_default(
            "company"
        )
        if company:
            cargo_registration.company = company

        appended_rows = []
        for row in valid_rows:
            source = source_rows.get(row.cargo_id)
            cargo_route = (source or {}).get("cargo_route") or row.cargo_route
            loading_date = (source or {}).get("loading_date") or row.expected_loading_date
            expected_offloading_date = (source or {}).get("expected_offloading_date") or row.expected_offloading_date
            cargo_location_country = (source or {}).get("cargo_location_country") or row.cargo_location_country
            cargo_location_city = (source or {}).get("cargo_location_city") or row.cargo_loading_city
            cargo_destination_country = (source or {}).get("cargo_destination_country") or row.cargo_destination_country
            cargo_destination_city = (source or {}).get("cargo_destination_city") or row.cargo_destination_city

            missing_fields = []
            if not cargo_route:
                missing_fields.append("cargo_route")
            if not loading_date:
                missing_fields.append("loading_date")
            if not expected_offloading_date:
                missing_fields.append("expected_offloading_date")
            if not cargo_location_country:
                missing_fields.append("cargo_location_country")
            if not cargo_location_city:
                missing_fields.append("cargo_location_city")
            if not cargo_destination_country:
                missing_fields.append("cargo_destination_country")
            if not cargo_destination_city:
                missing_fields.append("cargo_destination_city")

            if missing_fields:
                frappe.throw(
                    f"Manifest row {row.idx} is missing required values for Cargo Registration creation: "
                    f"{', '.join(missing_fields)}"
                )

            cargo_registration.append(
                "cargo_details",
                {
                    "cargo_id": (source or {}).get("cargo_id") or row.cargo_id,
                    "cargo_type": (source or {}).get("cargo_type") or row.cargo_type,
                    "container_size": (source or {}).get("container_size")
                    or row.container_size
                    or "Loose",
                    "seal_number": (source or {}).get("seal_number") or row.seal_number,
                    "bl_number": (source or {}).get("bl_number") or row.bl_number,
                    "cargo_route": cargo_route,
                    "net_weight": (source or {}).get("net_weight") or row.weight or 0,
                    "number_of_packages": (source or {}).get("number_of_packages")
                    or row.number_of_package
                    or 0,
                    "container_number": (source or {}).get("container_number")
                    or row.container_number,
                    "service_item": (source or {}).get("service_item")
                    or "Transportation Service",
                    "currency": (source or {}).get("currency")
                    or frappe.defaults.get_user_default("Currency")
                    or "USD",
                    "rate": (source or {}).get("rate") or 0,
                    "cargo_location_country": cargo_location_country,
                    "cargo_location_city": cargo_location_city,
                    "loading_date": loading_date,
                    "cargo_destination_country": cargo_destination_country,
                    "cargo_destination_city": cargo_destination_city,
                    "expected_offloading_date": expected_offloading_date,
                    "manifest_number": self.name,
                },
            )
            appended_rows.append(row)

        if not cargo_registration.cargo_details:
            frappe.throw(
                "Unable to create Cargo Registration because no valid Manifest cargo rows were found."
            )

        cargo_registration.insert(ignore_permissions=True)
        self.db_set("cargo_registration", cargo_registration.name, update_modified=False)

        # Keep downstream logic consistent by linking each manifest row to created Cargo Detail names.
        for index, row in enumerate(appended_rows):
            created_row = cargo_registration.cargo_details[index]
            row.cargo_id = created_row.name
            if row.name:
                frappe.db.set_value(
                    "Manifest Cargo Details",
                    row.name,
                    "cargo_id",
                    created_row.name,
                    update_modified=False,
                )

    def get_source_cargo_details(self):
        cargo_ids = [d.cargo_id for d in self.manifest_cargo_details if d.cargo_id]
        if not cargo_ids:
            return {}

        cargo_ids = list(dict.fromkeys(cargo_ids))

        source_details_by_name = frappe.get_all(
            "Cargo Detail",
            filters={"name": ["in", cargo_ids]},
            fields=[
                "name",
                "parent",
                "cargo_id",
                "cargo_type",
                "container_size",
                "seal_number",
                "bl_number",
                "cargo_route",
                "net_weight",
                "number_of_packages",
                "container_number",
                "service_item",
                "currency",
                "rate",
                "cargo_location_country",
                "cargo_location_city",
                "loading_date",
                "cargo_destination_country",
                "cargo_destination_city",
                "expected_offloading_date",
            ],
        )

        source_details_by_cargo_id = frappe.get_all(
            "Cargo Detail",
            filters={"cargo_id": ["in", cargo_ids]},
            fields=[
                "name",
                "parent",
                "cargo_id",
                "cargo_type",
                "container_size",
                "seal_number",
                "bl_number",
                "cargo_route",
                "net_weight",
                "number_of_packages",
                "container_number",
                "service_item",
                "currency",
                "rate",
                "cargo_location_country",
                "cargo_location_city",
                "loading_date",
                "cargo_destination_country",
                "cargo_destination_city",
                "expected_offloading_date",
            ],
        )

        source_details = {}
        for d in source_details_by_name + source_details_by_cargo_id:
            source_details[d.name] = d

        by_name = {}
        for d in source_details.values():
            by_name[d.name] = d
            if d.get("cargo_id"):
                by_name[d.get("cargo_id")] = d

        parent_names = list({d.parent for d in source_details.values() if d.parent})

        parent_map = {}
        if parent_names:
            parents = frappe.get_all(
                "Cargo Registration",
                filters={"name": ["in", parent_names]},
                fields=["name", "customer", "company"],
            )
            parent_map = {p.name: p for p in parents}

        for d in by_name.values():
            parent_info = parent_map.get(d.parent, {})
            d["parent_customer"] = parent_info.get("customer")
            d["parent_company"] = parent_info.get("company")

        return by_name

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
