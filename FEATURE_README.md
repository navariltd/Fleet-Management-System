# Feature: Automated Sales Invoice Creation from Cargo Registrations

## 🎯 Overview

This feature enables automatic creation of Sales Invoices directly from Cargo Registrations, including vehicle and truck details from associated Manifests.

**Branch**: `feat/auto_sales_invoice`  
**Status**: ✅ Ready for Testing  
**Date**: December 18, 2025

## 📦 What's Included

### New Files

- `vsd_fleet_ms/custom/sales_invoice_customization.py` - Backend API methods
- `vsd_fleet_ms/custom/sales_invoice_custom.js` - Frontend UI customization
- `vsd_fleet_ms/tests/test_invoice_automation.py` - Automated tests
- `docs/features/automated_invoice_creation.md` - Complete documentation
- `docs/features/quick_reference_invoice.md` - Quick reference guide
- `docs/features/visual_guide_invoice.md` - Visual diagrams and workflows
- `install_invoice_feature.sh` - Installation script
- `IMPLEMENTATION_SUMMARY.md` - Implementation details

### Modified Files

- `vsd_fleet_ms/hooks.py` - Added JavaScript and event hooks

## 🚀 Quick Start

### Installation

```bash
cd /home/muchemi/frappe-bench

# Pull the latest changes
git pull origin feat/auto_sales_invoice

# Build and restart
bench build --app vsd_fleet_ms
bench clear-cache
bench restart
```

Or use the installation script:

```bash
cd /home/muchemi/frappe-bench/apps/vsd_fleet_ms
./install_invoice_feature.sh
```

## 📋 Features

### For Users

✅ **One-Click Invoice Creation**  
Select customer → Click "Get Items From" → Select cargo → Done!

✅ **Automatic Truck Details**  
Vehicle number, driver name, and route automatically included

✅ **Smart Filtering**  
Only shows uninvoiced cargo for the selected customer

✅ **Prevent Double-Invoicing**  
Once cargo is invoiced, it won't appear again

✅ **Invoice Cancellation Support**  
Cancel invoice → Cargo becomes available again

### For Administrators

✅ **Extensible Architecture**  
Clean separation of concerns (backend/frontend)

✅ **Comprehensive Logging**  
All operations logged for audit trail

✅ **Test Suite Included**  
Automated tests for validation

✅ **Well Documented**  
Multiple documentation files for different audiences

## 📖 Documentation

| Document                                                                  | Purpose                | Audience        |
| ------------------------------------------------------------------------- | ---------------------- | --------------- |
| [Automated Invoice Creation](docs/features/automated_invoice_creation.md) | Complete feature guide | Everyone        |

## 🎨 User Interface

### Before

❌ Manual process:

1. Go to Cargo Registration
2. Select rows manually
3. Click "Create Invoice" button
4. Limited to one cargo registration at a time

### After

✅ Streamlined process:

1. Go to Sales Invoice
2. Select customer
3. Click "Get Items From" → "Cargo Registrations"
4. Select from ALL uninvoiced cargo across all registrations
5. One invoice for multiple cargo registrations

## 🔍 How It Works

### Data Flow

```
Cargo Registration → Manifest → Sales Invoice
      ↓                 ↓            ↓
  Cargo Details    Truck Info    Invoice Items
                                (with descriptions)
```

### Key Components

1. **`get_uninvoiced_cargo_details()`**

   - Fetches uninvoiced cargo for customer
   - Enriches with Manifest data
   - Returns formatted list

2. **`create_sales_invoice_from_cargo_details()`**

   - Creates Sales Invoice
   - Adds items with rich descriptions
   - Updates cargo detail references

3. **`update_cargo_detail_on_invoice_cancel()`**
   - Clears references on cancellation
   - Makes cargo available again
