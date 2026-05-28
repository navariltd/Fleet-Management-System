// Copyright (c) 2026, VV SYSTEMS DEVELOPER LTD and contributors
// For license information, please see license.txt

frappe.query_reports["Vehicle Trip Report"] = {
  filters: [
    {
      fieldname: "from_date",
      label: __("From Date"),
      fieldtype: "Date",
    },
    {
      fieldname: "to_date",
      label: __("To Date"),
      fieldtype: "Date",
    },
    {
      fieldname: "loading_location",
      label: __("Loading Place"),
      fieldtype: "Link",
      options: "Trip Locations",
    },
    {
      fieldname: "offloading_location",
      label: __("Offloading Place"),
      fieldtype: "Link",
      options: "Trip Locations",
    },
    {
      fieldname: "customer",
      label: __("Customer"),
      fieldtype: "Link",
      options: "Customer",
    },
    {
      fieldname: "driver_name",
      label: __("Driver"),
      fieldtype: "Data",
    },
    {
      fieldname: "trailer",
      label: __("Trailer"),
      fieldtype: "Link",
      options: "Assigned Trailers",
    },
    {
      fieldname: "truck_number",
      label: __("Plate Number"),
      fieldtype: "Link",
      options: "Truck",
    },
    {
      fieldname: "delivery_note",
      label: __("Delivery Note"),
      fieldtype: "Data",
    },
  ],
};
