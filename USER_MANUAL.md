# IDMC Vendor Portal — User Manual

**Version 1.3 · June 2026 · Classification: Internal — Restricted**

---

## Table of Contents

**Vendor Users**
1. [Introduction for Vendors](#1-introduction-for-vendors)
2. [Getting Started — First Login](#2-getting-started--first-login)
3. [Vendor Login (returning users)](#3-vendor-login-returning-users)
4. [Session Management — Staying Logged In](#4-session-management--staying-logged-in)
5. [Uploading Files](#5-uploading-files)
6. [Running Script Operations](#6-running-script-operations)
7. [Logging Out](#7-logging-out)
8. [Vendor Troubleshooting](#8-vendor-troubleshooting)

**Administrator Users**
9. [Introduction for Administrators](#9-introduction-for-administrators)
10. [Admin Login](#10-admin-login)
11. [Dashboard](#11-dashboard)
12. [Vendor Management](#12-vendor-management)
13. [Device Registry](#13-device-registry)
14. [Session Overview](#14-session-overview)
15. [Audit Log Viewer](#15-audit-log-viewer)
16. [Extensions Manager](#16-extensions-manager)
17. [Log Analyser](#17-log-analyser)
18. [LLM Settings](#18-llm-settings)
19. [Admin Troubleshooting](#19-admin-troubleshooting)

---

# Part I — Vendor Users

---

## 1. Introduction for Vendors

The **IDMC Vendor Portal** is a secure web interface that allows authorised vendor organisations to:

- **Upload files** (PM scripts, data files, parameter files) directly into Informatica Data Management Cloud staging directories — without requiring VPN access or shared filesystem credentials.
- **Trigger pre-approved scripts** on the IDMC host, such as daily data load jobs or parameter reload operations.

Your access is protected by a **password + one-time code** (two-factor authentication). You will need the **Google Authenticator** app installed on your smartphone. Your Informatica administrator will provide your username, password, and a QR code to scan during your first login.

### What you need

- A modern web browser (Chrome, Edge, Firefox, or Safari)
- Your assigned username and password (provided by your Informatica administrator)
- Google Authenticator installed on your smartphone:
  - [Google Authenticator on iOS App Store](https://apps.apple.com/app/google-authenticator/id388497605)
  - [Google Authenticator on Google Play](https://play.google.com/store/apps/details?id=com.google.android.apps.authenticator2)
- The QR code provided by your administrator (required only once, during your first login)

---

## 2. Getting Started — First Login

Before you can log in for the first time, your administrator will:
1. Create your vendor account in the system.
2. Show you a QR code (either on screen or via secure message).

You must scan this QR code into Google Authenticator **before** attempting to log in.

### Step 1 — Scan the QR code into Google Authenticator

1. Open **Google Authenticator** on your phone.
2. Tap the **+** button (bottom right) to add a new account.
3. Select **Scan a QR code**.
4. Point your camera at the QR code provided by your administrator.
5. A new entry labelled **IDMC Portal: \<your username\>** will appear in the app, showing a 6-digit code that refreshes every 30 seconds.

> **Important:** Once you have scanned the QR code and confirmed the entry appears in Google Authenticator, notify your administrator. The QR code cannot be displayed again — if it is lost or you switch phones, your administrator must generate a new one for you.

### Step 2 — Log in for the first time

1. Navigate to the portal URL provided by your administrator (e.g., `https://portal.your-company.com`).
2. Click **Vendor Login** (or navigate to `/login`).
3. Enter your **Username** and **Password**, then click **Continue**.
4. The page will ask for your **Authentication code** — open Google Authenticator, find the IDMC Portal entry, and enter the current 6-digit code.
5. Click **Verify**. You are now logged in.

---

## 3. Vendor Login (returning users)

1. Navigate to the portal URL.
2. Click **Vendor Login**.
3. Enter your **Username** and **Password**, click **Continue**.
4. Open **Google Authenticator** on your phone and find the IDMC Portal entry.
5. Enter the current 6-digit code in the **Authentication code** field, then click **Verify**.

> **Tips:**
> - TOTP codes refresh every 30 seconds. If you see the code is about to change, wait for the next one — entering a code in its last few seconds can sometimes fail if there is slight clock drift.
> - You have 3 TOTP attempts before the login form is briefly locked. If locked, wait 60 seconds and try again.
> - The server enforces an additional lockout after 5 failed attempts within 10 minutes — if this happens, contact your administrator.

---

## 4. Session Management — Staying Logged In

Vendor sessions last **30 minutes** from the time you log in. You will see a status bar at the top of the portal showing your remaining session time.

### Session renewal

When fewer than **5 minutes** remain, a banner appears at the top of the page:

> *"Your session expires in X minutes. Renew now to stay logged in."*

To renew:
1. Click **Renew session** in the banner.
2. A dialog will ask for a fresh 6-digit code from Google Authenticator.
3. Enter the current code and confirm.
4. Your session will be extended by another 30 minutes.

If the banner does not appear or you dismiss it, your session will expire and you will be redirected to the login page. Any in-progress upload at that moment will need to be restarted.

---

## 5. Uploading Files

The **File Upload** panel is the default view when you log in.

### Choosing a target directory

Use the **Target directory** dropdown to select where the file should be placed. The available directories depend on your role:

| Directory | Available to |
|---|---|
| `pm_scripts` | All vendors |
| `source_files` | All vendors |
| `parameter_files` | All vendors |
| `target_files` | Premium vendors only |

If a directory does not appear in your dropdown, your role does not permit uploads to that location. Contact your administrator if you believe you should have access.

### Selecting a file

You can select a file in two ways:
- **Drag and drop** a file from your computer onto the dashed drop zone.
- Click **Browse** to open a standard file picker.

The selected filename will appear in the drop zone once chosen.

**File size limit:** 500 MB per upload.

**Allowed file types:** The portal enforces a whitelist of allowed extensions. The default list includes: `.py`, `.sh`, `.sql`, `.csv`, `.txt`, `.xml`, `.json`, `.yaml`, `.yml`, `.properties`, `.conf`, `.cfg`. Your administrator can adjust this list. If you upload a file with a disallowed extension, you will see an error message listing the currently allowed types.

### Uploading

1. Select the target directory.
2. Select your file (drag-and-drop or Browse).
3. Click **Upload**.
4. A progress indicator shows the upload percentage. For large files this may take some time — do not close the tab.
5. On success, a confirmation message shows the uploaded filename and the timestamp.
6. On failure, an error message explains the cause (e.g., session expired, file type not allowed, file too large).

> **Filename note:** Filenames are automatically sanitised by the server. Characters such as `/`, `\`, `..`, `;`, backticks, and other shell metacharacters are removed. The displayed success message shows the sanitised filename as saved on the server.

---

## 6. Running Script Operations

The **Script Operations** panel is accessible from the left sidebar (click **Script Operations**).

The operations available to you are determined by your vendor role and are configured by your administrator. If no operations appear, none are currently assigned to your role.

### Running an operation

1. Locate the operation you want to run (e.g., "daily_load").
2. Read the operation description.
3. Click **Run**.
4. The button changes to **Running…** and an elapsed-time counter appears.
5. Wait for the operation to complete. Most operations take a few seconds; the maximum allowed time is 120 seconds.
6. On completion, the result panel shows:
   - **Exit code** — `0` indicates success; non-zero indicates the script reported an error.
   - **Duration** — time taken in milliseconds.
   - **Output** — the first 2,000 characters of the combined script output (stdout + stderr).

> **Note:** Operations run scripts on the IDMC host server. They are pre-approved by your administrator; you cannot run arbitrary commands. The output shown is informational — contact your administrator if an unexpected exit code appears.

### Operation timeout

If an operation runs for more than 120 seconds, it is automatically terminated and you will see:

> *"Operation timed out after 120 seconds."*

This is a safety limit. Contact your administrator if a legitimate operation requires more time.

---

## 7. Logging Out

Click **Log out** at the bottom of the left sidebar. Your session is immediately invalidated on the server and you are redirected to the login page.

> **Tip:** Always log out when you have finished using the portal, especially on shared computers.

---

## 8. Vendor Troubleshooting

### "Login failed" when entering my password

- Check that your username is spelled correctly (case-sensitive).
- Ensure Caps Lock is off.
- Contact your administrator if you have forgotten your password — there is no self-service password reset.

### "Login failed" when entering my TOTP code

- Check that the 6-digit code is entered before it refreshes (the code changes every 30 seconds). If it's about to change, wait for the next one.
- Ensure your phone's clock is accurate. Google Authenticator relies on the system clock. If the time on your phone is significantly off, TOTP codes will not work. Enable automatic time sync in your phone's settings.
- Ensure you are scanning the correct entry in Google Authenticator — look for the one labelled **IDMC Portal: \<your username\>**.

### "Too many attempts. Try again in Xs."

The client-side form is briefly locking you out after 3 incorrect TOTP attempts. Wait the displayed number of seconds and try again.

### I replaced my phone and lost Google Authenticator

Contact your administrator. They will revoke your old TOTP device and generate a new QR code for you to scan.

### "You do not have permission to upload to this directory"

Your vendor role does not have access to the selected directory. Either choose a different directory from the dropdown, or contact your administrator to check your role assignment.

### "File type '.\<ext\>' is not permitted"

The file extension is not in the current allowed list. The error message will display the currently permitted extensions. Either rename your file to a permitted extension, or ask your administrator to add the extension to the whitelist.

### "File exceeds the maximum allowed size (500 MB)"

The file you selected is larger than the 500 MB limit. You may need to split or compress the file before uploading.

### The upload progress bar shows 100% but no success message appears

This can happen if your session expired during a large upload. Log in again and retry the upload.

### The session renewal banner appeared but I dismissed it, and now I'm logged out

Sessions expire after 30 minutes of inactivity or if the session is not renewed. Log in again. Your uploaded files are not affected — uploads that completed before the session expired are already on the server.

---

# Part II — Administrator Users

---

## 9. Introduction for Administrators

The **IDMC Admin Console** is the management interface for the portal. Access it at `/admin/login` (or click **Administrator Login** on the landing page).

As an administrator you can:
- Create and manage vendor accounts (including TOTP device setup)
- Revoke vendor devices and reset TOTP enrollment
- Monitor and force-expire active sessions
- View the full audit log (with filters and CSV export)
- Browse the IDMC staging directory tree
- Analyse log files using an AI assistant
- Configure the AI provider and model
- Manage the allowed file extension whitelist

Admin accounts use **password authentication only** (no TOTP). Protect your admin password carefully — admin sessions last 8 hours and grant access to all management functions.

---

## 10. Admin Login

1. Navigate to `https://your-portal-host/admin/login`.
2. Enter your **Username** and **Password**.
3. Click **Sign in**.

You are redirected to the Admin Dashboard.

**Account lockout:** After 10 consecutive failed login attempts within a 15-minute window, further attempts are blocked. If you are locked out, wait 15 minutes or contact another administrator to reset your access.

---

## 11. Dashboard

The Dashboard provides a live overview of portal activity, auto-refreshing every **30 seconds**.

### Stat cards

| Card | What it shows |
|---|---|
| Active Vendors | Count of vendor accounts with `active = true` |
| Enrolled Devices | Count of non-revoked TOTP devices across all vendors |
| Active Sessions | Count of sessions that have not expired or been invalidated |
| Audit Events (24h) | Count of audit log entries in the last 24 hours |

### Recent Audit Events table

Displays the 20 most recent audit log entries with:
- **Timestamp** — UTC datetime of the event
- **Event** — colour-coded badge (green = success, red = failure/revocation, blue = info, yellow = warning)
- **Vendor** — vendor ID if the event involves a vendor (dash otherwise)
- **Source IP** — client IP at the time of the event

Click **Refresh** to force an immediate update. The last refresh time is shown in the top right.

---

## 12. Vendor Management

Navigate to **Admin Console → Vendors**.

### Vendor list

The table shows all registered vendors with:
- **ID** — internal vendor identifier
- **Username** — login name
- **Role** — `standard` or `premium` badge
- **Created** — creation date (UTC)
- **Status** — `Active` (green) or `Inactive` (red)
- **Devices** — total device count (including revoked)
- **Actions** — Deactivate button (active vendors only)

### Creating a vendor

1. Click **+ Create Vendor**.
2. Fill in the **Username**, **Password**, and **Role** (`Standard` or `Premium`).
3. Click **Create**.

The system will immediately:
- Create the vendor account.
- Generate a new TOTP seed.
- Display a **QR code dialog** with the TOTP QR code.

**Show the QR code to the vendor** (on screen or by sending the `otpauth://` URI via a secure channel). The QR code is displayed only once. If the vendor misses it, use the **Re-issue QR** button in the Device Registry (see §13).

> **Password policy:** Set a strong initial password. Vendors cannot change their own password — if a reset is needed, deactivate the vendor and create a new account, or contact your system administrator to update the password hash directly in the database.

### Deactivating a vendor

1. Click **Deactivate** in the vendor's row.
2. A confirmation dialog warns that all associated TOTP devices will be revoked and all active sessions terminated immediately.
3. Click **Confirm** to proceed.

Deactivation is **not reversible** from the UI. The vendor record remains in the database with `active = false`. A deactivated vendor cannot log in. All their sessions become invalid immediately.

---

## 13. Device Registry

Navigate to **Admin Console → Devices**, or from a vendor's row click **Devices** (when that link is present).

The table shows all enrolled TOTP devices with:
- **ID** — internal device ID
- **Vendor ID** — owning vendor
- **UUID suffix** — last 8 characters of the device UUID hash (for identification)
- **Enrolled at** — enrollment datetime
- **Status** — `Active` or `Revoked`
- **Revoked at** — revocation datetime (if revoked)
- **Last used at** — last successful TOTP verification against this device

### Re-issuing a QR code (vendor switched phones or lost authenticator)

If a vendor needs a new QR code:

1. Navigate to **Devices** and find the vendor's current device.
2. Click **Re-issue QR** (or go to **Vendors**, find the vendor, and click **Re-issue enrollment link**).
3. The system will:
   - Revoke the vendor's existing active device.
   - Generate a new TOTP seed.
   - Display a new QR code.
4. Have the vendor scan the new QR code into Google Authenticator.

> The old device is revoked atomically with the creation of the new one — there is no window during which the vendor is without an active device.

### Revoking a specific device

To revoke a device without issuing a replacement (e.g., suspected compromise):
1. In the Device Registry table, find the device.
2. Click **Revoke**.
3. Confirm the action.

The vendor will no longer be able to log in until a new device is issued.

---

## 14. Session Overview

Navigate to **Admin Console → Sessions**.

The table shows all currently **active** (non-expired, non-invalidated) sessions:
- **ID** — internal session ID
- **Subject ID** — vendor ID or admin ID
- **Type** — `vendor` or `admin`
- **Role** — role embedded in the session
- **Created at** — session creation time
- **Last active** — last time the session was used for a validated request
- **Expires at** — when the session will automatically expire
- **Source IP** — client IP at login time

### Force-expiring a session

To immediately terminate a session (e.g., suspected compromise or accidental shared login):

1. Find the session in the table.
2. Click **Force Expire**.
3. Confirm the action.

The session is invalidated immediately. The next request using the associated cookie will receive a 401 response and be redirected to the login page.

---

## 15. Audit Log Viewer

Navigate to **Admin Console → Audit Log**.

The audit log is a permanent, append-only record of all security-relevant events.

### Filters

| Filter | Description |
|---|---|
| **Vendor ID** | Show only events for a specific vendor |
| **Event type** | Show only events of a specific type (e.g., `vendor_login_failure`) |
| **Date from / Date to** | Filter by date range (ISO format: `YYYY-MM-DD`) |

Click **Search** to apply filters. Pagination controls appear at the bottom of the table.

### Event types reference

| Event type | Meaning |
|---|---|
| `vendor_login_success` | Vendor successfully logged in |
| `vendor_login_failure` | Vendor login failed (wrong password or TOTP) |
| `admin_login_success` | Admin successfully logged in |
| `admin_login_failure` | Admin login failed |
| `enrollment` | New TOTP device enrolled for vendor |
| `re_enrollment` | Admin re-issued a new QR code (old device revoked) |
| `vendor_created` | New vendor account created |
| `vendor_deactivation` | Vendor account deactivated (devices revoked, sessions invalidated) |
| `device_revocation` | Individual TOTP device revoked |
| `force_expire_session` | Admin force-expired an active session |

### CSV export

To export the currently filtered results as a CSV file, click **Export CSV**. The download will contain: ID, event type, subject ID, subject type, vendor ID, device UUID hash, timestamp, and source IP.

---

## 16. Extensions Manager

Navigate to **Admin Console → Extensions**.

This page controls which file extensions vendors are allowed to upload.

### Current extensions

The current whitelist is displayed as a list of extensions (e.g., `.py`, `.csv`, `.sh`).

### Editing the extension list

1. Click **Edit**.
2. The list becomes editable. Add or remove extensions:
   - Each extension must start with a `.` (dot)
   - Only alphanumeric characters are allowed after the dot (e.g., `.csv` not `.tar.gz`)
   - Maximum 16 characters per extension
3. Click **Save**.

Changes take effect **immediately** for all subsequent upload requests. There is no restart required.

> **Important:** Removing an extension will prevent vendors from uploading that file type immediately, including any uploads already in progress. Ensure vendors are informed before removing extensions they depend on.

---

## 17. Log Analyser

Navigate to **Admin Console → Log Analyser**.

The Log Analyser is a three-panel interface:
- **Left panel** — File browser (IDMC staging directory tree)
- **Centre panel** — File content viewer
- **Right panel** — AI chat assistant

### Browsing files

The left panel shows the IDMC staging directory tree. Click any directory to expand it. Click a file to select and load it.

The centre panel will display:
- File metadata (path, size, line count, service label, encoding)
- A sensitivity warning if the file content matches known patterns for credentials or secrets (e.g., `password=`, `token=`, `api_key=`)
- The raw file content (scrollable)

### Automatic analysis

If the file does not appear to contain sensitive data, an AI analysis begins **automatically** as soon as the file loads. The right panel (AI Chat) will stream the analysis results.

If the file is flagged as potentially sensitive:
1. A yellow warning banner appears in the centre panel.
2. You must click **"I understand — analyse anyway"** to send the file content to the external AI provider.
3. This step exists to ensure you are aware that log file content is sent externally.

> **Data policy note:** When you use the Log Analyser, the selected file's content is sent to the configured external LLM provider (e.g., Anthropic, OpenAI). Ensure your organisation's data-handling policy permits sending this data to the configured provider before proceeding. Do not analyse files containing credentials, PII, or confidential business data.

### Re-running analysis

Click **Analyse** (in the centre panel toolbar) at any time to re-run the initial analysis for the currently loaded file.

### Asking follow-up questions

The right panel contains a chat interface. Type a question in the text box at the bottom and press **Enter** or click **Send**. The AI will answer in the context of the currently loaded file.

Example questions:
- "What is the most recent error in this log?"
- "Are there any repeated failures in the last hour?"
- "What IDMC mapping generated these errors?"
- "Summarise the error pattern in one sentence."

Click **Clear chat** to reset the conversation history. This does not reload the file.

### AI analysis structure

The initial analysis always follows this structure:
1. **Summary** — what the log records and the time range covered
2. **Errors and warnings** — each listed with timestamp and severity
3. **Anomalies** — unexpected patterns, repeated failures, timing gaps
4. **Root cause** — most likely cause if errors are present
5. **Recommended next steps**

### Large files

Files larger than `max_context_tokens × 4` characters are automatically trimmed. The most recent lines are kept (most relevant for log analysis). The system prompt includes a note explaining how many lines were omitted. You can see the current token limit in **Admin Console → LLM Settings**.

---

## 18. LLM Settings

Navigate to **Admin Console → Settings → LLM Settings**.

This page configures the AI provider used by the Log Analyser.

### Provider selection

Click one of the four provider tiles:
- **Anthropic Claude** — Claude models (Opus, Sonnet, Haiku)
- **OpenAI** — GPT-4o and other OpenAI models
- **Azure OpenAI** — GPT models deployed via Azure
- **Google Gemini** — Gemini models via Google AI Studio

### Model

Enter the exact model identifier for your chosen provider. Examples:
- Anthropic: `claude-opus-4-8`, `claude-sonnet-4-6`
- OpenAI: `gpt-4o`, `gpt-4-turbo`
- Azure OpenAI: the deployment name (not the model name)
- Google Gemini: `gemini-2.0-flash`, `gemini-1.5-pro`

### API Key

Enter the API key for the selected provider. The key is stored encrypted on the server and is never displayed in plaintext after saving.

If you leave the field blank and click **Save**, the existing stored key is preserved (indicated by the masked placeholder `sk-a••••••••XXXX`).

> **Key sources:**
> - Anthropic: https://console.anthropic.com/
> - OpenAI: https://platform.openai.com/
> - Azure OpenAI: Azure Portal → your OpenAI resource → Keys and Endpoints
> - Google Gemini: https://aistudio.google.com/

### Azure-specific fields

When **Azure OpenAI** is selected, two additional fields appear:
- **Azure endpoint** — the full HTTPS endpoint URL (e.g., `https://your-resource.openai.azure.com/`)
- **Azure deployment name** — the name of your deployment in Azure OpenAI Studio

### Max context tokens

Controls how many tokens of log file content are sent to the LLM. Files that exceed this threshold are trimmed (most recent lines kept).

- Range: 1,000 – 200,000
- Default: 80,000
- Set higher to analyse larger log files in full; set lower if the provider's context limit is smaller or you want to reduce API costs.

### Saving and testing

1. Make your changes.
2. Click **Save changes**.
3. Click **Test connection** to verify the API key and model are valid. A green "✓ Connected (Xms)" message confirms success.

> If the test fails with "API key not valid" or similar, re-enter the API key (the field shows `••••` and you must type it again to update the stored value).

---

## 19. Admin Troubleshooting

### Cannot log in — "Login failed"

- Verify the username and password are correct.
- Check if an account lockout is in effect (10 failed attempts within 15 minutes). Wait 15 minutes before retrying, or contact another admin.
- Check `docker compose logs auth-service --tail 50` for `admin_login_failure` events.

### A vendor cannot log in after being created

Ensure the QR code was scanned successfully. In the Device Registry, confirm the vendor has at least one active (non-revoked) device. If the device count is 0, go to **Vendors → Re-issue enrollment link** to generate a new QR code.

### A vendor reports "Authentication failed" on TOTP even after scanning a new QR code

Check that the vendor's phone clock is synchronised (automatic time). TOTP is time-based; a clock that is more than ±90 seconds off will cause all codes to fail.

### Vendor deactivation revoked devices and sessions but vendor is still logged in on one device

Force-expire the specific session via **Sessions → Force Expire**. Session invalidation takes effect immediately on the next request made with that session cookie.

### Log Analyser shows "Error: HTTP 503"

The LLM provider is unreachable. Check:
1. The API key in **LLM Settings** is correct (use **Test connection**).
2. The backend-api container can reach the internet (check DNS and firewall).

### Log Analyser streams "[LLM ERROR] No API key configured"

No API key has been saved yet. Go to **LLM Settings**, enter the API key, and save.

### Log Analyser says "File too large" for a file under 10 MB

Files are limited to 10 MB for reading into the browser. If the file is larger, it needs to be trimmed on the server before analysis. Contact your system administrator.

### The extension list was changed but vendors still see the old allowed extensions

Extension changes are in-memory and take effect immediately on the backend. Confirm by checking the **Extensions** page — the list shown is always the current live list. If a vendor is still getting an "extension not permitted" error for a now-allowed extension, ask them to clear their browser cache and retry.

### "docker compose logs" shows auth-service crashes on startup

Look for `FATAL: required environment variable` messages. Check that all required environment variables are set in `.env`. See DEPLOYMENT.md §6 and §8 for the full list and generation commands.

### How do I reset an admin's password?

There is no self-service password reset. Use the `seed_admin.py` script:

```bash
docker compose exec auth-service python seed_admin.py \
    --username <admin_username> \
    --password "<new_password>"
```

The script detects the existing account and updates the password hash. Record the new password securely.

---

*End of User Manual — IDMC Vendor Portal v1.3 — June 2026*
