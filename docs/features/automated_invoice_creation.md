# Automated Sales Invoice Creation from Cargo Registrations

## Overview

This feature allows you to automatically create Sales Invoices from Cargo Registrations, including fetching vehicle/truck details from assigned Manifests.

## Features Implemented

### 1. Cargo Registration Tracking

- **Invoice Field**: The existing `invoice` field in Cargo Detail (child table) tracks which invoice a cargo detail is linked to
- **Service Item**: Each cargo detail must have a service item specified
- **Manifest Integration**: Truck/vehicle details are fetched from assigned Manifests

### 2. Sales Invoice Enhancement

- **New Button**: "Cargo Registrations" added under "Get Items From" dropdown
- **Smart Filtering**: Only shows uninvoiced cargo details for the selected customer
- **Truck Details**: Automatically includes truck/vehicle information from Manifests
- **Description**: Rich description including vehicle number, driver name, route, and trip info

### 3. Safeguards

- **Double-Invoice Prevention**: Once a cargo detail is invoiced, it won't appear in future fetches
- **Invoice Cancellation Handling**: If an invoice is cancelled, cargo details are unmarked automatically
- **Validation**: Ensures customer and company are selected before fetching

## Usage Instructions

### Creating a Sales Invoice from Cargo Registrations

1. **Create/Open Sales Invoice**

   - Go to Sales Invoice
   - Select a **Customer**
   - Select a **Company**

2. **Fetch Cargo Registrations**
   - Click on **"Get Items From"** dropdown (top right area)
   - Select **"Cargo Registrations"**
3. **Select Cargo Details**

   - A dialog will appear showing all uninvoiced cargo details for that customer
   - The dialog shows:
     - Cargo Registration number
     - Route
     - Cargo Type
     - Weight (in tonnes)
     - Truck/Vehicle (from Manifest)
     - Manifest number
   - Check the cargo details you want to invoice
   - Click **"Add to Invoice"**

4. **Review and Submit**
   - The system will create a new invoice with all selected cargo details
   - Each line item includes:
     - Service Item
     - Quantity (based on weight if "Bill on Weight" is enabled)
     - Rate
     - Rich description with truck/driver/route details
   - Review the invoice
   - Submit when ready

### What Happens Behind the Scenes

1. **On Invoice Creation**:

   - Selected cargo details are added as invoice items
   - Truck/vehicle details are fetched from assigned Manifests
   - Each cargo detail's `invoice` field is set to the invoice number
   - Description includes vehicle number, driver, route, and trip info

2. **On Invoice Submission**:

   - Cargo details remain linked to the invoice
   - These cargo details won't appear in future fetch operations

3. **On Invoice Cancellation**:
   - All cargo detail references are automatically cleared
   - Those cargo details become available for invoicing again

## Technical Details

### Files Created/Modified

1. **`vsd_fleet_ms/custom/sales_invoice_customization.py`**

   - Server-side methods for fetching and processing cargo details
   - Methods:
     - `get_uninvoiced_cargo_details()`: Fetches uninvoiced cargo
     - `create_sales_invoice_from_cargo_details()`: Creates invoice from cargo
     - `build_item_description()`: Builds rich descriptions with truck details
     - `update_cargo_detail_on_invoice_cancel()`: Clears references on cancellation

2. **`vsd_fleet_ms/custom/sales_invoice_custom.js`**

   - Client-side UI for Sales Invoice
   - Adds "Cargo Registrations" button
   - Shows selection dialog
   - Handles user interactions

3. **`vsd_fleet_ms/hooks.py`**
   - Registers JavaScript file for Sales Invoice
   - Adds document event hook for invoice cancellation

### Database Schema

**Cargo Detail (Child Table)**:

- `invoice` (Link to Sales Invoice): Tracks which invoice the cargo is linked to
- `service_item` (Link to Item): The service item to bill
- `manifest_number` (Link to Manifest): Links to the assigned manifest
- `rate` (Currency): Rate for the service
- `allow_bill_on_weight` (Check): Whether to bill based on weight
- `net_weight_tonne` (Float): Weight in tonnes

**Sales Invoice Item**:

- `cargo_id` (Data): Reference to Cargo Detail ID

### Flow Diagram

```
Cargo Registration (with Cargo Details)
           ↓
    Assign to Manifest
           ↓
      Manifest (contains truck/driver details)
           ↓
Sales Invoice → "Get Items From" → "Cargo Registrations"
           ↓
    Dialog shows uninvoiced cargo details
           ↓
    User selects cargo details
           ↓
Sales Invoice created with truck/vehicle details
           ↓
Cargo Details marked as invoiced
```
