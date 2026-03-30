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
			"fieldname": "offloading_location",
			"label": "Offloading Place",
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
			rs.offloading_location
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

	return " AND ".join(conditions), values


def get_offloading_data(filters):
	pass


def get_onloading_data(filters):
	pass
