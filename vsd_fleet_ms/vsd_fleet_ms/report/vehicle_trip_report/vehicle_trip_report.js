// Copyright (c) 2026, VV SYSTEMS DEVELOPER LTD and contributors
// For license information, please see license.txt

frappe.query_reports["Vehicle Trip Report"] = {
  filters: [
    {
      fieldname: "vehicle_trip",
      label: __("Vehicle Trip"),
      fieldtype: "Link",
      options: "Trips",
    },
    {
      fieldname: "truck_number",
      label: __("Plate Number"),
      fieldtype: "Link",
      options: "Truck",
    },
    {
      fieldname: "driver_name",
      label: __("Assigned Driver"),
      fieldtype: "Data",
    },
    {
      fieldname: "cargo_type",
      label: __("Cargo Type"),
      fieldtype: "Link",
      options: "Cargo Types",
    },
  ],
};
