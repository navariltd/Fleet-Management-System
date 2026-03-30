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
			"label": "Truck Number",
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
	]
	return columns


def get_data(filters):
	where_clause, values = apply_filters(filters)

	return frappe.db.sql(
		f"""
		SELECT
			name AS vehicle_trip,
			truck_number,
			driver_name
		FROM `tabTrips`
		WHERE {where_clause}
		ORDER BY modified DESC
		""",
		values,
		as_dict=True,
	)


def apply_filters(filters):
	filters = filters or {}
	conditions = ["docstatus < 2"]
	values = {}

	if filters.get("vehicle_trip"):
		conditions.append("name = %(vehicle_trip)s")
		values["vehicle_trip"] = filters.get("vehicle_trip")

	if filters.get("truck_number"):
		conditions.append("truck_number = %(truck_number)s")
		values["truck_number"] = filters.get("truck_number")

	if filters.get("driver_name"):
		conditions.append("driver_name LIKE %(driver_name)s")
		values["driver_name"] = f"%{filters.get('driver_name')}%"

	return " AND ".join(conditions), values


def get_offloading_data(filters):
	pass


def get_onloading_data(filters):
	pass
