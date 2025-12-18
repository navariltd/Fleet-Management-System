// Copyright (c) 2025, VV SYSTEMS DEVELOPER LTD and contributors
// For license information, please see license.txt

frappe.ui.form.on("Sales Invoice", {
  onload: function (frm) {
    add_fetch_cargo_button(frm);
  },

  refresh: function (frm) {
    add_fetch_cargo_button(frm);
  },

  customer: function (frm) {
    add_fetch_cargo_button(frm);
  },

  on_submit: function (frm) {
    frappe.show_alert(
      {
        message: __("Cargo Details have been linked to this invoice"),
        indicator: "green",
      },
      5
    );
  },
});

function add_fetch_cargo_button(frm) {
  if (frm.doc.docstatus === 0 && frm.doc.customer && frm.doc.company) {
    frm.remove_custom_button(__("Cargo Registrations"), __("Get Items From"));
    frm.add_custom_button(
      __("Cargo Registrations"),
      function () {
        fetch_and_show_cargo_details(frm);
      },
      __("Get Items From")
    );
  }
}

function fetch_and_show_cargo_details(frm) {
  frappe.call({
    method:
      "vsd_fleet_ms.custom.sales_invoice_customization.get_uninvoiced_cargo_details",
    args: {
      customer: frm.doc.customer,
      company: frm.doc.company,
    },
    callback: function (r) {
      if (r.message && r.message.length > 0) {
        show_cargo_selection_dialog(frm, r.message);
      } else {
        frappe.msgprint({
          title: __("No Uninvoiced Cargo"),
          message: __(
            "No uninvoiced Cargo Registrations found for customer {0}",
            [frm.doc.customer]
          ),
          indicator: "orange",
        });
      }
    },
  });
}

function show_cargo_selection_dialog(frm, cargo_details) {
  var dialog = new frappe.ui.Dialog({
    title: __("Select Cargo Details to Invoice"),
    fields: [
      {
        fieldname: "cargo_details",
        fieldtype: "Table",
        label: __("Cargo Details"),
        cannot_add_rows: true,
        cannot_delete_rows: true,
        in_place_edit: false,
        data: cargo_details,
        fields: [
          {
            fieldname: "parent",
            label: __("Cargo Registration"),
            fieldtype: "Link",
            options: "Cargo Registration",
            in_list_view: 1,
            read_only: 1,
            columns: 2,
          },
          {
            fieldname: "cargo_route",
            label: __("Route"),
            fieldtype: "Data",
            in_list_view: 1,
            read_only: 1,
            columns: 2,
          },
          {
            fieldname: "cargo_type",
            label: __("Type"),
            fieldtype: "Data",
            in_list_view: 1,
            read_only: 1,
            columns: 1,
          },
          {
            fieldname: "net_weight_tonne",
            label: __("Weight (Tonnes)"),
            fieldtype: "Float",
            in_list_view: 1,
            read_only: 1,
            columns: 1,
          },
          {
            fieldname: "truck_license_plate",
            label: __("Truck"),
            fieldtype: "Data",
            in_list_view: 1,
            read_only: 1,
            columns: 2,
          },
          {
            fieldname: "manifest_number",
            label: __("Manifest"),
            fieldtype: "Link",
            options: "Manifest",
            in_list_view: 1,
            read_only: 1,
            columns: 2,
          },
          {
            fieldname: "name",
            label: __("Cargo ID"),
            fieldtype: "Data",
            hidden: 1,
          },
        ],
      },
      {
        fieldtype: "HTML",
        fieldname: "help_text",
        options:
          '<p class="text-muted small">Select cargo details to add to this invoice. Only uninvoiced cargo is shown.</p>',
      },
    ],
    primary_action_label: __("Add to Invoice"),
    primary_action: function (values) {
      var selected_cargo = [];

      dialog.fields_dict.cargo_details.grid.grid_rows.forEach(function (row) {
        if (row.doc.__checked) {
          selected_cargo.push(row.doc.name);
        }
      });

      if (selected_cargo.length === 0) {
        frappe.msgprint(__("Please select at least one Cargo Detail"));
        return;
      }

      add_cargo_to_invoice(frm, selected_cargo, dialog);
    },
    secondary_action_label: __("Cancel"),
    secondary_action: function () {
      dialog.hide();
    },
  });

  dialog.fields_dict.cargo_details.grid.wrapper.find(".grid-add-row").hide();
  dialog.fields_dict.cargo_details.grid.wrapper
    .find(".grid-remove-rows")
    .hide();

  dialog.show();
  dialog.$wrapper.find(".modal-dialog").css("max-width", "80%");
}

function add_cargo_to_invoice(frm, selected_cargo_ids, dialog) {
  frappe.call({
    method:
      "vsd_fleet_ms.custom.sales_invoice_customization.create_sales_invoice_from_cargo_details",
    args: {
      customer: frm.doc.customer,
      company: frm.doc.company,
      cargo_detail_ids: selected_cargo_ids,
    },
    freeze: true,
    freeze_message: __("Creating Sales Invoice..."),
    callback: function (r) {
      if (r.message) {
        dialog.hide();

        frappe.set_route("Form", "Sales Invoice", r.message.name);

        frappe.show_alert(
          {
            message: __("Sales Invoice created with {0} items", [
              selected_cargo_ids.length,
            ]),
            indicator: "green",
          },
          5
        );
      }
    },
  });
}
