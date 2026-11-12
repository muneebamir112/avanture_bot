# Avanture Listing Automation Desktop Application

A modern desktop application built with **Python**, **CustomTkinter**, and **Playwright** for automated bulk publishing to https://www.avanture.net/classifieds with **Role-Based Access Control (Super Admin & Admin)**.

---

## Access Control Architecture (Super Admin & Admins)

The application enforces role-based security:

1. **Super Admin**:
   - Master account (`superadmin`).
   - Has full access to the automation tool and the **"🛡️ Manage Admins"** panel.
   - Can create new Admin accounts.
   - Can **revoke access** from any Admin at any time with a single click.
   - Can **restore access** or delete Admin accounts.
   - Live Permission Checks: If an Admin's access is revoked while they have the app open, their execution is instantly terminated.

2. **Admins (Staff / Operators)**:
   - Created and managed by the Super Admin.
   - Can log into the application and publish listings if status is **Active**.
   - If status is set to **Revoked**, they are blocked from logging in or executing tasks.

### Default Super Admin Credentials
- **Username**: `superadmin`
- **Password**: `admin123`

---

## Exact DOM Mappings Implemented

| Field | DOM Selector |
| :--- | :--- |
| **New Listing Button** | `a[href*='/classifieds/edit']`, `:has-text('New Listing')` |
| **Title** | `#input_edit_classifieds_listing_data_title` (max 50 chars) |
| **Category** | `#input_edit_classifieds_listing_data_category` (values 5 to 27) |
| **Description** | `#input_edit_classifieds_listing_data_body` (50 to 1000 chars) |
| **Country** | `#input_edit_classifieds_listing_data_location_country` |
| **State** | `#input_edit_classifieds_listing_data_location_state` (AJAX dynamic) |
| **City** | `#input_edit_classifieds_listing_data_location_city` (AJAX dynamic) |
| **Registry Number** | `#input_edit_classifieds_listing_data_maticna_stevilka` (Conditional) |
| **Submit** | `button[type='submit']`, `:has-text('Save')`, `:has-text('Objavi')` |

---

## How to Run

1. Open PowerShell:
   ```powershell
   cd e:\WebNcodes\avan
   ```

2. Start the application:
   ```powershell
   python app.py
   ```

3. Sign in as Super Admin (`superadmin` / `admin123`).
4. Click **"🛡️ Manage Admins"** to create or manage your admin users!
