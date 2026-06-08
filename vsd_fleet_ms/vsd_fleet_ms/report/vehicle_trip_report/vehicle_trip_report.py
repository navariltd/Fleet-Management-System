# Copyright (c) 2026, VV SYSTEMS DEVELOPER LTD and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_columns():
    columns = [
        {
            "fieldname": "vehicle_trip",
            "label": "Vehicle Trip",
            "fieldtype": "Link",
            "options": "Trips",
            "width": 150,
        },
        {
            "fieldname": "truck_number",
            "label": "Plate Number",
            "fieldtype": "Link",
            "options": "Truck",
            "width": 150,
        },
        {
            "fieldname": "trailer_1",
            "label": "Trailer",
            "fieldtype": "Link",
            "options": "Assigned Trailers",
            "width": 150,
        },
        {
            "fieldname": "driver_name",
            "label": "Driver",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "loading_date",
            "label": "Loading Date",
            "fieldtype": "Date",
            "width": 120,
        },
        {
            "fieldname": "loading_location",
            "label": "Loading Place",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "peage_expense",
            "label": "Peage",
            "fieldtype": "Currency",
            "width": 120,
        },
        {
            "fieldname": "fm_expense",
            "label": "FM",
            "fieldtype": "Currency",
            "width": 120,
        },
        {"fieldname": "product", "label": "Product", "fieldtype": "Data", "width": 220},
        {
            "fieldname": "loaded_weight",
            "label": "Qty Loaded",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "fieldname": "fuel_stock_out",
            "label": "Fuel",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "fieldname": "offloading_location",
            "label": "Offloading Place",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "offloading_date",
            "label": "Offloading Date",
            "fieldtype": "Date",
            "width": 120,
        },
        {
            "fieldname": "offloaded_weight",
            "label": "Qty Offloaded",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "fieldname": "delivery_note",
            "label": "Delivery Note",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "customer",
            "label": "Customer",
            "fieldtype": "Link",
            "options": "Customer",
            "width": 180,
        },
        {
            "fieldname": "load_difference",
            "label": "Qty Difference",
            "fieldtype": "Data",
            "width": 120,
        },
    ]
    return columns


def get_data(filters):
    where_clause, values = apply_filters(filters)

    return frappe.db.sql(
        f"""
		SELECT
			t.name AS vehicle_trip,
            t.fuel_stock_out,
			t.truck_number,
            t.trailer_1,
			t.driver_name,
			rs.loading_date,
			rs.loading_location,
			rfd.peage_expense,
			rfd.fm_expense,
			mcd.product,
			rs.loaded_weight,
			COALESCE(frt.approved_fuel, 0) AS approved_fuel,
			rs.offloading_location,
			rs.offloading_date,
			rs.offloaded_weight,
			t.custom_delivery_note AS delivery_note,
			mcd.customer,
			(COALESCE(rs.offloaded_weight, 0) - COALESCE(rs.loaded_weight, 0)) AS load_difference
		FROM `tabTrips` t
		LEFT JOIN (
			SELECT
				parent,
				MAX(CASE WHEN location_type = 'Loading Point' THEN loading_date END) AS loading_date,
				MAX(CASE WHEN location_type = 'Loading Point' THEN location END) AS loading_location,
				MAX(CASE WHEN location_type = 'Offloading Point' THEN offloading_date END) AS offloading_date,
				MAX(CASE WHEN location_type = 'Offloading Point' THEN location END) AS offloading_location,
				MAX(CASE WHEN location_type = 'Loading Point' THEN load_qty END) AS loaded_weight,
				MAX(CASE WHEN location_type = 'Offloading Point' THEN load_qty END) AS offloaded_weight
			FROM `tabRoute Steps`
			WHERE parenttype = 'Trips' AND parentfield = 'main_route_steps'
			GROUP BY parent
		) rs ON rs.parent = t.name
		LEFT JOIN (
			SELECT
				parent,
				MAX(CASE WHEN expense_type = 'Peage' THEN request_amount END) AS peage_expense,
				MAX(CASE WHEN expense_type = 'FM' THEN request_amount END) AS fm_expense
			FROM `tabRequested Fund Details`
			WHERE parenttype = 'Trips' AND parentfield = 'requested_fund_accounts_table'
			GROUP BY parent
		) rfd ON rfd.parent = t.name
		LEFT JOIN (
			SELECT
				parent,
				GROUP_CONCAT(cargo_type ORDER BY idx SEPARATOR ', ') AS product,
				GROUP_CONCAT(customer_name ORDER BY idx SEPARATOR ', ') AS customer
			FROM `tabManifest Cargo Details`
			WHERE parenttype = 'Manifest'
			  AND parentfield = 'manifest_cargo_details'
			  AND IFNULL(cargo_type, '') != ''
			GROUP BY parent
		) mcd ON mcd.parent = t.manifest
		LEFT JOIN (
			SELECT
				parent,
				SUM(CASE WHEN status = 'Approved' THEN quantity ELSE 0 END) AS approved_fuel
			FROM `tabFuel Requests Table`
			WHERE parenttype = 'Trips' AND parentfield = 'fuel_request_history'
			GROUP BY parent
		) frt ON frt.parent = t.name
		LEFT JOIN `tabAssigned Trailers` at ON (
			at.parent = t.name AND at.parenttype = 'Trips' AND at.parentfield IN ('trailer_1', 'trailer_2', 'trailer_3')
		)
		WHERE {where_clause}
		ORDER BY t.modified DESC
		""",
        values,
        as_dict=True,
    )


def apply_filters(filters):
    filters = filters or {}
    conditions = ["t.docstatus = 1"]
    values = {}

    if filters.get("from_date"):
        conditions.append("rs.loading_date >= %(from_date)s")
        values["from_date"] = filters.get("from_date")

    if filters.get("to_date"):
        conditions.append("rs.offloading_date <= %(to_date)s")
        values["to_date"] = filters.get("to_date")

    if filters.get("loading_location"):
        conditions.append("rs.loading_location = %(loading_location)s")
        values["loading_location"] = filters.get("loading_location")

    if filters.get("offloading_location"):
        conditions.append("rs.offloading_location = %(offloading_location)s")
        values["offloading_location"] = filters.get("offloading_location")

    if filters.get("customer"):
        conditions.append("""EXISTS (
				SELECT 1
				FROM `tabManifest Cargo Details` mcd_filter
				WHERE mcd_filter.parent = t.manifest
				  AND mcd_filter.customer_name = %(customer)s
			)""")
        values["customer"] = filters.get("customer")

    if filters.get("driver_name"):
        conditions.append("t.driver_name LIKE %(driver_name)s")
        values["driver_name"] = f"%{filters.get('driver_name')}%"

    if filters.get("trailer"):
        conditions.append("""EXISTS (
				SELECT 1
				FROM `tabAssigned Trailers` at_filter
				WHERE at_filter.parent = t.name
				  AND at_filter.parenttype = 'Trips'
				  AND at_filter.name = %(trailer)s
			)""")
        values["trailer"] = filters.get("trailer")

    if filters.get("truck_number"):
        conditions.append("t.truck_number = %(truck_number)s")
        values["truck_number"] = filters.get("truck_number")

    if filters.get("delivery_note"):
        conditions.append("t.custom_delivery_note = %(delivery_note)s")
        values["delivery_note"] = filters.get("delivery_note")

    return " AND ".join(conditions), values
