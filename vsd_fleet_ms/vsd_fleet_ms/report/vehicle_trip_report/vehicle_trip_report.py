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
			"width": 150
		},
		{
			"fieldname": "truck_number",
			"label": "Plate Number",
			"fieldtype": "Link",
			"options": "Truck",
			"width": 150
		},
		{
			"fieldname": "driver_name",
			"label": "Assigned Driver",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "loading_date",
			"label": "Loading Date",
			"fieldtype": "Date",
			"width": 120
		},
		{
			"fieldname": "loading_location",
			"label": "Loading Place",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "offloading_date",
			"label": "Offloading Date",
			"fieldtype": "Date",
			"width": 150
		},
		{
			"fieldname": "peage_expense",
			"label": "Peage",
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"fieldname": "peage_expense_status",
			"label": "Peage Status",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "fm_expense",
			"label": "FM",
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"fieldname": "fm_expense_status",
			"label": "FM Status",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "cargo_types",
			"label": "Cargo Types",
			"fieldtype": "Data",
			"width": 220
		},
		{
			"fieldname": "approved_fuel",
			"label": "Fuel",
			"fieldtype": "Data",
			"width": 150
		}
		{
			"fieldname": "loaded_weight",
			"label": "Qty Loaded (Kg)",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "offloaded_weight",
			"label": "Qty Offloaded (Kg)",
			"fieldtype": "Data",
			"width": 150
		},
	]
	return columns


def get_data(filters):
	where_clause, values = apply_filters(filters)

	return frappe.db.sql(
		f"""
		SELECT
			t.name AS vehicle_trip,
			t.truck_number,
			t.driver_name,
			rs.loading_date,
			rs.loading_location,
			rs.offloading_date,
			rs.offloading_location,
			rfd.peage_expense,
			rfd.peage_expense_status,
			rfd.fm_expense,
			rfd.fm_expense_status,
			mcd.cargo_types,
			mcd.loaded_weight,
			COALESCE(frt.approved_fuel, 0) AS approved_fuel
		FROM `tabTrips` t
		LEFT JOIN (
			SELECT
				parent,
				MAX(CASE WHEN location_type = 'Loading Point' THEN loading_date END) AS loading_date,
				MAX(CASE WHEN location_type = 'Loading Point' THEN location END) AS loading_location,
				MAX(CASE WHEN location_type = 'Offloading Point' THEN offloading_date END) AS offloading_date,
				MAX(CASE WHEN location_type = 'Offloading Point' THEN location END) AS offloading_location
			FROM `tabRoute Steps`
			WHERE parenttype = 'Trips' AND parentfield = 'main_route_steps'
			GROUP BY parent
		) rs ON rs.parent = t.name
		LEFT JOIN (
			SELECT
				parent,
				MAX(CASE WHEN expense_type = 'Peage' THEN request_amount END) AS peage_expense,
				MAX(CASE WHEN expense_type = 'Peage' THEN request_status END) AS peage_expense_status,
				MAX(CASE WHEN expense_type = 'FM' THEN request_amount END) AS fm_expense,
				MAX(CASE WHEN expense_type = 'FM' THEN request_status END) AS fm_expense_status
			FROM `tabRequested Fund Details`
			WHERE parenttype = 'Trips' AND parentfield = 'requested_fund_accounts_table'
			GROUP BY parent
		) rfd ON rfd.parent = t.name
		LEFT JOIN (
			SELECT
				parent,
				GROUP_CONCAT(cargo_type ORDER BY idx SEPARATOR ', ') AS cargo_types,
				GROUP_CONCAT(weight ORDER BY idx SEPARATOR ', ') AS loaded_weight
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

	if filters.get("vehicle_trip"):
		conditions.append("t.name = %(vehicle_trip)s")
		values["vehicle_trip"] = filters.get("vehicle_trip")

	if filters.get("truck_number"):
		conditions.append("t.truck_number = %(truck_number)s")
		values["truck_number"] = filters.get("truck_number")

	if filters.get("driver_name"):
		conditions.append("t.driver_name LIKE %(driver_name)s")
		values["driver_name"] = f"%{filters.get('driver_name')}%"

	if filters.get("cargo_type"):
		conditions.append(
			"""EXISTS (
				SELECT 1
				FROM `tabManifest Cargo Details` mcd_filter
				WHERE mcd_filter.parent = t.manifest
				  AND mcd_filter.cargo_type = %(cargo_type)s
			)"""
		)
		values["cargo_type"] = filters.get("cargo_type")

	return " AND ".join(conditions), values
