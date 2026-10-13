from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

doc = Document()

# ── Page margins ──────────────────────────────────────────────────────────────
for section in doc.sections:
    section.top_margin    = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin   = Inches(1.2)
    section.right_margin  = Inches(1.2)

# ── Colour palette ────────────────────────────────────────────────────────────
DARK_BLUE  = RGBColor(0x1F, 0x39, 0x64)
MID_BLUE   = RGBColor(0x2E, 0x74, 0xB5)
ACCENT     = RGBColor(0x00, 0x70, 0xC0)
WHITE      = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GREY = RGBColor(0xF2, 0xF2, 0xF2)
TEXT       = RGBColor(0x26, 0x26, 0x26)
RED        = RGBColor(0xC0, 0x00, 0x00)
GREY_TEXT  = RGBColor(0x80, 0x80, 0x80)

# ── Helpers ───────────────────────────────────────────────────────────────────
def set_cell_bg(cell, rgb):
    hex_color = f"{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"),   "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"),  hex_color)
    tcPr.append(shd)

def code(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent  = Inches(0.3)
    p.paragraph_format.right_indent = Inches(0.3)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after  = Pt(4)
    pPr = p._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"),   "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"),  "F5F5F5")
    pPr.append(shd)
    run = p.add_run(text)
    run.font.name  = "Courier New"
    run.font.size  = Pt(8.5)
    run.font.color.rgb = RGBColor(0x20, 0x20, 0x20)
    return p

def h1(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after  = Pt(4)
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(18)
    run.font.color.rgb = DARK_BLUE
    return p

def h2(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after  = Pt(3)
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(13)
    run.font.color.rgb = MID_BLUE
    return p

def h3(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(7)
    p.paragraph_format.space_after  = Pt(2)
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(11)
    run.font.color.rgb = MID_BLUE
    return p

def body(doc, text, bold=False):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(text)
    run.bold = bold
    run.font.size = Pt(10.5)
    run.font.color.rgb = TEXT
    return p

def bul(doc, text, level=0):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.left_indent = Inches(0.25 + 0.2 * level)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(text)
    run.font.size = Pt(10)
    run.font.color.rgb = TEXT
    return p

def table(doc, headers, rows, col_widths=None):
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.LEFT
    hdr = t.rows[0]
    for i, h in enumerate(headers):
        cell = hdr.cells[i]
        cell.text = ""
        run = cell.paragraphs[0].add_run(h)
        run.bold = True
        run.font.size = Pt(9.5)
        run.font.color.rgb = WHITE
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_cell_bg(cell, ACCENT)
    for r_idx, row in enumerate(rows):
        bg = LIGHT_GREY if r_idx % 2 == 0 else WHITE
        for c_idx, val in enumerate(row):
            cell = t.rows[r_idx + 1].cells[c_idx]
            cell.text = ""
            run = cell.paragraphs[0].add_run(str(val))
            run.font.size = Pt(9.5)
            run.font.color.rgb = TEXT
            set_cell_bg(cell, bg)
    if col_widths:
        for i, w in enumerate(col_widths):
            for row in t.rows:
                row.cells[i].width = Inches(w)
    return t

def hr(doc):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after  = Pt(6)
    pPr  = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bot  = OxmlElement("w:bottom")
    bot.set(qn("w:val"),   "single")
    bot.set(qn("w:sz"),    "6")
    bot.set(qn("w:space"), "1")
    bot.set(qn("w:color"), "2E74B5")
    pBdr.append(bot)
    pPr.append(pBdr)

# ═══════════════════════════════════════════════════════════════════════════════
# TITLE PAGE
# ═══════════════════════════════════════════════════════════════════════════════
p = doc.add_paragraph()
p.paragraph_format.space_before = Inches(1.5)
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("IDMC Vendor File Portal")
run.bold = True; run.font.size = Pt(28); run.font.color.rgb = DARK_BLUE

p2 = doc.add_paragraph()
p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
run2 = p2.add_run("Design, Architecture & Test Harness Document")
run2.font.size = Pt(16); run2.font.color.rgb = MID_BLUE

doc.add_paragraph()
p3 = doc.add_paragraph()
p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
run3 = p3.add_run("Version 1.1  ·  May 2026")
run3.font.size = Pt(11); run3.font.color.rgb = GREY_TEXT

doc.add_paragraph()
p4 = doc.add_paragraph()
p4.alignment = WD_ALIGN_PARAGRAPH.CENTER
run4 = p4.add_run("Classification: Internal — Restricted")
run4.bold = True; run4.font.size = Pt(10); run4.font.color.rgb = RED

doc.add_page_break()

# ═══════════════════════════════════════════════════════════════════════════════
# TABLE OF CONTENTS
# ═══════════════════════════════════════════════════════════════════════════════
h1(doc, "Table of Contents")
toc = [
    "1.  Executive Summary",
    "2.  System Overview & Goals",
    "3.  Architecture Design",
    "    3.1  High-Level Topology",
    "    3.2  Tier 1 — Native Mobile App",
    "    3.3  Tier 2 — Web Portal (SPA + Backend API)",
    "    3.4  Tier 3 — Auth Service & Device Registry",
    "    3.5  Tier 4 — IDMC Filesystem Layer",
    "4.  Authentication & Session Design",
    "    4.1  Enrollment Flow",
    "    4.2  Login Flow",
    "    4.3  Session Lifecycle",
    "    4.4  Revocation",
    "5.  Security Model",
    "6.  Data Flow Diagrams",
    "7.  Test Harness Design",
    "    7.1  Layer 1 — Mobile App Tests",
    "    7.2  Layer 2 — Web Portal Tests",
    "    7.3  Layer 3 — Auth Service Tests",
    "    7.4  Layer 4 — Backend API Tests",
    "    7.5  Cross-Layer Integration Tests",
    "8.  AI Build Prompts",
    "    8.1  How to Use the Prompts",
    "    8.2  Prompt 1 — Auth Service & Device Registry",
    "    8.3  Prompt 2 — Backend API",
    "    8.4  Prompt 3 — Web Portal SPA",
    "    8.5  Prompt 4 — Native Mobile App",
    "    8.6  Prompt 5 — Test Harness",
    "    8.7  Prompt 6 — Infrastructure & Deployment",
    "9.  Deployment & Operations",
    "10. Environment Variables — Complete Guide",
    "    10.1  Full Variable List",
    "    10.2  Step 1 — Generate Each Secret",
    "    10.3  Step 2 — Store Secrets Securely (Linux)",
    "    10.4  Step 2 — Store Secrets Securely (Windows)",
    "    10.5  Step 3 — What Never To Do",
    "    10.6  Step 4 — How Services Read Variables",
    "    10.7  Step 5 — Per-Environment Strategy",
    "    10.8  generate-secrets.sh",
    "    10.9  Summary Decision Tree",
    "11. Open Questions & Future Enhancements",
]
for item in toc:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(item)
    run.font.size = Pt(10); run.font.color.rgb = TEXT
doc.add_page_break()

# ═══════════════════════════════════════════════════════════════════════════════
# 1. EXECUTIVE SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
h1(doc, "1. Executive Summary")
body(doc, (
    "This document describes the complete design of the IDMC Vendor File Portal — a lightweight, "
    "multi-tier web application that allows external vendors to upload files into specific "
    "Informatica IDMC Secure Agent staging directories, and optionally trigger pre-approved "
    "scripts, without requiring full remote desktop or SSH access."
))
body(doc, (
    "The solution consists of four tiers: a native mobile authenticator app, a browser-based "
    "vendor portal, a dedicated authentication service with device registry, and a hardened "
    "backend API that mediates all filesystem and script operations. Authentication uses "
    "device-bound TOTP (RFC 6238) with hardware-backed key storage — no credentials are ever "
    "visible in application code, config files, or transmitted after initial enrollment."
))
body(doc, "Key properties:")
bul(doc, "Runs on Windows Server and Linux without modification")
bul(doc, "Vendors need only a browser and the enrolled mobile app — no VPN, no RDP, no SSH client")
bul(doc, "All secrets loaded from OS secret stores or environment variables — never hardcoded")
bul(doc, "Path traversal, credential injection, session hijacking, and replay attacks are explicitly mitigated")
bul(doc, "Each tier is independently testable with defined doubles for all external dependencies")
hr(doc)

# ═══════════════════════════════════════════════════════════════════════════════
# 2. SYSTEM OVERVIEW & GOALS
# ═══════════════════════════════════════════════════════════════════════════════
h1(doc, "2. System Overview & Goals")
h2(doc, "2.1  Problem Statement")
body(doc, (
    "Vendors need to deliver files to specific IDMC Secure Agent directories (PM scripts, "
    "source/target data files, user parameter files) and occasionally trigger scheduled scripts. "
    "Currently this requires either full RDP access (over-privileged) or manual handoff via "
    "shared drives (no audit trail, no access control). Neither approach is acceptable for a "
    "production integration platform."
))
h2(doc, "2.2  Goals")
table(doc,
    ["Goal", "Success Criterion"],
    [
        ["Least-privilege access", "Vendors can reach only their assigned directories and approved scripts"],
        ["No credential exposure", "No service credentials visible in code, config, or API responses"],
        ["Cross-platform", "Runs unmodified on Windows Server 2019+ and Ubuntu 22.04+"],
        ["Vendor simplicity", "Vendor needs only a browser + enrolled phone"],
        ["Audit trail", "Every upload and script execution is logged with vendor identity, timestamp, and outcome"],
        ["Revocability", "A vendor's access can be fully revoked within one admin action, effective immediately"],
    ],
    col_widths=[2.2, 4.3]
)
hr(doc)

# ═══════════════════════════════════════════════════════════════════════════════
# 3. ARCHITECTURE DESIGN
# ═══════════════════════════════════════════════════════════════════════════════
h1(doc, "3. Architecture Design")
h2(doc, "3.1  High-Level Topology")
body(doc, "Four tiers communicate strictly downward. No tier calls a higher tier.")
code(doc,
"""┌─────────────────────┐        ┌──────────────────────────┐
│  Tier 1             │        │  Tier 2                  │
│  Native Mobile App  │        │  Web Portal (SPA)        │
│  iOS / Android      │        │  Vendor's Browser        │
└────────┬────────────┘        └────────────┬─────────────┘
         │ TOTP code (manual)               │ HTTPS + HttpOnly cookie
         └──────────────┐   ┌───────────────┘
                        ▼   ▼
              ┌──────────────────────────┐
              │  Tier 3                  │
              │  Auth Service            │
              │  + Device Registry       │
              └────────────┬─────────────┘
                           │ Internal only
                           ▼
              ┌──────────────────────────┐
              │  Tier 4                  │
              │  Backend API             │
              │  File + Script Ops       │
              └────────────┬─────────────┘
                           │ OS filesystem calls
                           ▼
              ┌──────────────────────────┐
              │  IDMC Staging Directories│
              │  (Secure Agent Host)     │
              └──────────────────────────┘""")

h2(doc, "3.2  Tier 1 — Native Mobile App")
body(doc, "Technology: React Native (iOS + Android from single codebase) or Flutter.")
table(doc,
    ["Responsibility", "Detail"],
    [
        ["Device enrollment", "One-time setup: exchanges a single-use token for a TOTP seed over pinned TLS"],
        ["Device identity", "Generates a cryptographic UUID stored in hardware-backed keychain (iOS Secure Enclave / Android Keystore)"],
        ["TOTP generation", "RFC 6238 compliant; codes generated locally — nothing transmitted at login time"],
        ["Seed protection", "Seed stored in hardware keychain; never in plain storage, logs, or analytics"],
        ["TLS pinning", "Enrollment API certificate is pinned in the app bundle"],
    ],
    col_widths=[2.0, 4.5]
)

h2(doc, "3.3  Tier 2 — Web Portal (SPA + Backend API)")
body(doc, "Technology: React or Vue SPA. Backend: Python/FastAPI or Node/Express.")
table(doc,
    ["Responsibility", "Detail"],
    [
        ["Vendor login UI", "Username + password → TOTP prompt → session established"],
        ["Directory browser", "Shows only directories permitted by the vendor's RBAC role"],
        ["File upload", "Streams directly to backend; progress indicator; operation-scoped upload token"],
        ["Script triggers", "Named operation buttons; no raw script paths exposed to the browser"],
        ["Session management", "Displays inactivity countdown; prompts for OTP renewal at 25-minute mark"],
        ["Role-based rendering", "UI elements not permitted by the vendor's role are not rendered"],
    ],
    col_widths=[2.0, 4.5]
)

h2(doc, "3.4  Tier 3 — Auth Service & Device Registry")
body(doc, "Technology: Python/FastAPI or Go. Separate process. Not directly reachable from the public internet.")
table(doc,
    ["Responsibility", "Detail"],
    [
        ["Credential validation", "Validates username + bcrypt password hash"],
        ["TOTP validation", "RFC 6238 window check; replay protection via used-code cache"],
        ["Device registry", "Maps vendor accounts to enrolled device UUID hashes; enforces revocation"],
        ["JWT issuance", "RS256 signed tokens; claims include vendor ID, role, issued-at, hard expiry"],
        ["Enrollment API", "Accepts single-use token; issues TOTP seed once; stores only its hash"],
        ["Lockout enforcement", "Increments failed-attempt counter; enforces cooldown after threshold"],
        ["Admin API", "Revoke device, create enrollment link, view registry — admin-only routes"],
    ],
    col_widths=[2.0, 4.5]
)

h2(doc, "3.5  Tier 4 — IDMC Filesystem Layer (Backend API)")
body(doc, "Runs under a least-privilege OS service account.")
table(doc,
    ["Responsibility", "Detail"],
    [
        ["Path validation", "Resolves canonical path; compares against vendor-role allowlist before any filesystem call"],
        ["File write", "Atomic write via temp-file + rename; no partial files visible to IDMC agent"],
        ["Operation registry", "Maps operation name tokens to absolute script paths"],
        ["Script execution", "Spawns subprocess with fixed, sanitized environment"],
        ["Audit logging", "Structured log entry per upload and script execution"],
        ["Upload token", "Short-lived, operation-scoped token for large uploads"],
    ],
    col_widths=[2.0, 4.5]
)
hr(doc)

# ═══════════════════════════════════════════════════════════════════════════════
# 4. AUTHENTICATION & SESSION DESIGN
# ═══════════════════════════════════════════════════════════════════════════════
h1(doc, "4. Authentication & Session Design")
h2(doc, "4.1  Enrollment Flow")
code(doc,
"""Admin creates vendor account in registry
        │
        ▼
Admin sends one-time enrollment link (24-hour expiry, single-use)
        │
        ▼
Vendor installs native app (enterprise MDM or direct link)
        │
        ▼
Vendor opens enrollment deep link in the app
        │
        ▼
App generates device UUID → stores in hardware keychain
        │
        ▼
App sends (UUID + one-time token) to Enrollment API over pinned TLS
        │
        ▼
Server validates token → generates TOTP seed → returns seed once
        │
        ▼
App stores seed in hardware keychain → confirms enrollment
        │
        ▼
Server stores hash(seed) + hash(UUID) → invalidates enrollment token
        │
        ▼
Vendor can now log in at the web portal""")

h2(doc, "4.2  Login Flow")
code(doc,
"""Vendor opens browser portal
        │
        ▼
Enters username + password  ──→  Auth Service validates bcrypt hash
        │ success
        ▼
Portal prompts for 6-digit TOTP code
        │
        ▼
Vendor reads code from native app (locally generated, not transmitted)
        │
        ▼
Portal sends code to Auth Service
        │
        ▼
Auth Service: validates TOTP window + checks device UUID registered
            + checks device not revoked + checks code not replayed
        │ all pass
        ▼
Auth Service issues RS256 JWT → Portal stores in HttpOnly cookie""")

h2(doc, "4.3  Session Lifecycle")
table(doc,
    ["Parameter", "Value", "Rationale"],
    [
        ["Inactivity timeout",  "10 minutes",              "Unattended sessions expire quickly"],
        ["Hard maximum",        "30 minutes",              "Caps total session regardless of activity"],
        ["Renewal prompt",      "At 25-minute mark",       "Gives vendor 5 minutes to renew before hard expiry"],
        ["Renewal mechanism",   "New TOTP code in portal", "Re-validates device binding; resets to fresh 30-min window"],
        ["Upload token TTL",    "60 minutes from issuance","Allows large transfers without tying to session expiry"],
        ["Upload token scope",  "Single operation + dir",  "Cannot be reused for a different path"],
        ["Session storage",     "HttpOnly, Secure, SameSite=Strict cookie", "Inaccessible to JavaScript"],
    ],
    col_widths=[2.0, 1.8, 2.7]
)

h2(doc, "4.4  Revocation")
body(doc, "Revocation is synchronous — no cache window between admin action and enforcement.")
bul(doc, "Admin calls the Admin API to revoke a device UUID")
bul(doc, "Device registry sets the revoked flag atomically")
bul(doc, "All subsequent Auth Service validations fail immediately for that UUID")
bul(doc, "Active sessions using the revoked device UUID are invalidated on the next request")
hr(doc)

# ═══════════════════════════════════════════════════════════════════════════════
# 5. SECURITY MODEL
# ═══════════════════════════════════════════════════════════════════════════════
h1(doc, "5. Security Model")
table(doc,
    ["Threat", "Attack Vector", "Control"],
    [
        ["Password theft alone",         "Credential phishing",       "TOTP second factor required"],
        ["TOTP interception",            "MITM on login",             "TOTP never transmitted after enrollment; generated on-device"],
        ["Session hijacking",            "Cookie theft, XSS",         "HttpOnly + Secure + SameSite=Strict; short session window"],
        ["CSRF",                         "Forged cross-origin POST",  "SameSite=Strict + CSRF token on state-changing requests"],
        ["XSS",                          "Malicious filename",        "All filenames HTML-escaped; Content-Security-Policy header"],
        ["Path traversal",               "../ in upload path",        "Server resolves canonical path vs allowlist before any write"],
        ["Arbitrary script execution",   "Vendor-supplied script",    "Named operation registry only; no shell passthrough"],
        ["Credential injection via code","Developer accident",        "All secrets in env vars or OS secret store; service exits if absent"],
        ["IMEI spoofing",                "Hardware IMEI cloning",     "IMEI not used; cryptographic device UUID in hardware keychain"],
        ["OTP replay",                   "Capture and resubmit OTP",  "Used-code cache; each code valid once per 30s window"],
        ["Enrollment link reuse",        "Link interception",         "Single-use token invalidated atomically after first use"],
        ["Device stolen",                "Attacker has enrolled phone","Admin revokes UUID; enforcement is immediate"],
        ["User enumeration",             "Probe which factor failed", "All auth failures return identical generic error message"],
        ["Timing oracle",                "Measure response time",     "Constant-time comparison; response-time padding"],
        ["Secrets in subprocess env",    "Script reads parent env",   "Subprocess spawned with clean minimal environment only"],
    ],
    col_widths=[1.8, 1.8, 2.9]
)
hr(doc)

# ═══════════════════════════════════════════════════════════════════════════════
# 6. DATA FLOW DIAGRAMS
# ═══════════════════════════════════════════════════════════════════════════════
h1(doc, "6. Data Flow Diagrams")
h2(doc, "6.1  File Upload Flow")
code(doc,
"""Vendor Browser          Portal Backend        Auth Service      Filesystem
      │                         │                    │                 │
      │── POST /upload/request ▶│                    │                 │
      │   (session cookie)      │── validate JWT ───▶│                 │
      │                         │◀─ vendor role ─────│                 │
      │                         │── check path in    │                 │
      │                         │   role allowlist   │                 │
      │◀─ upload token ─────────│                    │                 │
      │                         │                    │                 │
      │── PUT /upload/{token} ─▶│                    │                 │
      │   (file bytes)          │── canonicalize     │                 │
      │                         │── write temp ──────────────────────▶│
      │                         │── atomic rename ───────────────────▶│
      │◀─ 200 OK ───────────────│                    │                 │
      │                         │── audit log        │                 │""")

h2(doc, "6.2  Script Execution Flow")
code(doc,
"""Vendor Browser          Portal Backend        Auth Service      Subprocess
      │                         │                    │                 │
      │── POST /operations/run ▶│                    │                 │
      │   (operation_name)      │── validate JWT ───▶│                 │
      │   (session cookie)      │◀─ vendor role ─────│                 │
      │                         │── lookup op in     │                 │
      │                         │   registry         │                 │
      │                         │── check role       │                 │
      │                         │── spawn subprocess ────────────────▶│
      │                         │   (clean env)      │                 │
      │                         │◀─ stdout/exit ──────────────────────│
      │◀─ 200 OK + output ──────│                    │                 │
      │                         │── audit log        │                 │""")
hr(doc)

# ═══════════════════════════════════════════════════════════════════════════════
# 7. TEST HARNESS DESIGN
# ═══════════════════════════════════════════════════════════════════════════════
h1(doc, "7. Test Harness Design")
body(doc, "Three governing rules apply across all layers:")
bul(doc, "No real credentials in any test fixture — all secrets injected via environment variables in the test runner")
bul(doc, "Each layer is testable in isolation — every external dependency has a defined fake or stub")
bul(doc, "Security tests are first-class — each layer has a dedicated security test suite")

h2(doc, "7.1  Layer 1 — Mobile App Tests")
h3(doc, "Unit Tests")
table(doc, ["Test", "Assertion"], [
    ["TOTP generation",            "Correct output for RFC 6238 reference vectors"],
    ["TOTP window acceptance",     "T-1, T, T+1 accepted; T-3 rejected"],
    ["Device UUID format",         "Non-empty, correctly formatted UUID"],
    ["Keychain roundtrip",         "Stored seed and UUID retrieved correctly"],
    ["Deep link parsing",          "Correct one-time token extracted"],
    ["Expired link",               "Rejected before any network call"],
    ["Keychain write failure",     "Enrollment aborted; no partial state"],
], col_widths=[2.5, 4.0])

h3(doc, "Integration Tests (local enrollment stub)")
table(doc, ["Test", "Assertion"], [
    ["Full enrollment flow",       "Seed stored in keychain after success"],
    ["Re-enrollment attempt",      "Rejected; no new seed stored"],
    ["Single-use token reuse",     "Second attempt rejected"],
    ["Network timeout",            "No partial keychain state"],
    ["TLS cert mismatch",          "Enrollment aborts; does not proceed silently"],
], col_widths=[2.5, 4.0])

h3(doc, "Security Tests")
table(doc, ["Test", "Assertion"], [
    ["Seed storage location",        "In hardware keychain; absent from plain storage"],
    ["Seed not in logs",             "Absent from log output and crash reports"],
    ["No post-enrollment transmit",  "App does not send seed or OTP after setup"],
    ["Certificate pin enforcement",  "Self-signed cert rejected even if OS trusts it"],
], col_widths=[2.5, 4.0])

h2(doc, "7.2  Layer 2 — Web Portal (SPA) Tests")
h3(doc, "Unit Tests")
table(doc, ["Test", "Assertion"], [
    ["Login form fields",         "Both fields rendered before and after password submission"],
    ["TOTP input validation",     "Accepts 6 digits; rejects letters, symbols"],
    ["Session countdown",         "Renders and decrements correctly"],
    ["Renewal prompt timing",     "Appears at 25-minute mark"],
    ["Upload states",             "Progress, completion, and failure states all render"],
    ["Script button during run",  "Disabled while operation is in flight"],
    ["Role-based rendering",      "Restricted vendor does not see unauthorised items"],
], col_widths=[2.5, 4.0])

h3(doc, "Integration Tests (contract mock API)")
table(doc, ["Test", "Assertion"], [
    ["Successful login sequence",   "Password → TOTP → session cookie set"],
    ["Failed first factor",         "Error shown; no TOTP prompt"],
    ["Failed TOTP",                 "Error shown; attempt counter incremented"],
    ["TOTP lockout",                "Form disabled for cooldown after N failures"],
    ["Session expiry",              "Detects expired session and redirects to login"],
    ["Upload to allowed path",      "Succeeds; confirmation shown"],
    ["Upload to forbidden path",    "Rejected by frontend guard and mock API"],
    ["Script trigger payload",      "Sends operation name token, not a path"],
    ["OTP renewal resets timer",    "Countdown resets after successful renewal"],
], col_widths=[2.8, 3.7])

h3(doc, "Security Tests")
table(doc, ["Test", "Assertion"], [
    ["Cookie attributes",       "HttpOnly and SameSite=Strict in Set-Cookie header"],
    ["No token in storage",     "localStorage and sessionStorage empty after login"],
    ["CSRF forged request",     "Cross-origin POST rejected"],
    ["XSS via filename",        "Script tag in filename rendered as escaped text"],
    ["Open redirect",           "Redirect to external domain rejected"],
], col_widths=[2.5, 4.0])

h2(doc, "7.3  Layer 3 — Auth Service Tests")
h3(doc, "Unit Tests — Auth Logic")
table(doc, ["Test", "Assertion"], [
    ["Valid TOTP accepted",         "Code for current window accepted"],
    ["Expired TOTP rejected",       "Code outside window rejected"],
    ["Replay rejection",            "Same code rejected on second submission"],
    ["JWT claims",                  "Correct vendor ID, role, iat, exp"],
    ["JWT alg:none rejected",       "Algorithm confusion attack blocked"],
    ["Expired JWT rejected",        "Structurally valid but expired JWT fails"],
    ["Constant-time comparison",    "Password hash check does not short-circuit"],
    ["Lockout counter",             "Increments on failure; resets on success"],
    ["Lockout enforcement",         "Correct TOTP still fails during lockout"],
    ["Lockout release",             "Correct TOTP succeeds after cooldown"],
], col_widths=[2.5, 4.0])

h3(doc, "Unit Tests — Device Registry")
table(doc, ["Test", "Assertion"], [
    ["UUID lookup",               "Returns correct record for known UUID hash"],
    ["Revoked UUID",              "Returns revoked status regardless of TOTP"],
    ["Valid enrollment",          "UUID hash and seed hash stored; token marked used"],
    ["Already-used token",        "Second enrollment rejected"],
    ["Expired token",             "Enrollment rejected"],
    ["Re-enrollment atomicity",   "Old UUID revoked and new UUID stored in same transaction"],
], col_widths=[2.5, 4.0])

h3(doc, "Security Tests")
table(doc, ["Test", "Assertion"], [
    ["Seed not recoverable",      "Only seed hash in DB; raw seed absent"],
    ["JWT key from env",          "Service refuses to start if JWT_SIGNING_KEY absent"],
    ["DB credentials from env",   "Service refuses to start if DB_URL absent"],
    ["Enrollment requires token", "Endpoint returns 401 without valid one-time token"],
    ["Rate limiting",             "More than N requests/min returns 429"],
    ["No user enumeration",       "Identical error for wrong password, TOTP, and unregistered device"],
    ["Response time padding",     "Timing does not reveal which factor failed"],
], col_widths=[2.5, 4.0])

h2(doc, "7.4  Layer 4 — Backend API Tests")
h3(doc, "Unit Tests")
table(doc, ["Test", "Assertion"], [
    ["Path canonicalization",        "Relative path resolved and compared to allowlist"],
    ["Path traversal — literal",     "../ rejected before filesystem call"],
    ["Path traversal — encoded",     "..%2F and double-encoded variants rejected"],
    ["File type validation",         "Disallowed extension returns 400 before write"],
    ["File size validation",         "Oversized file returns 413 before write"],
    ["Operation registry hit",       "operation_name maps to correct script path"],
    ["Operation registry miss",      "Unknown name returns 400; no filesystem call"],
    ["Subprocess environment",       "No service secrets in script subprocess env"],
    ["Upload token scope",           "Token cannot be reused for second upload"],
], col_widths=[2.5, 4.0])

h3(doc, "Integration Tests (temp filesystem + script stubs)")
table(doc, ["Test", "Assertion"], [
    ["Upload to allowed path",    "File appears in correct temp directory"],
    ["Upload to forbidden path",  "Returns 403; nothing written"],
    ["Path traversal payload",    "Rejected at validation; nothing written"],
    ["Allowed script trigger",    "Stub executes and result returned"],
    ["Forbidden script trigger",  "Returns 403"],
    ["Concurrent uploads",        "Both files written correctly; no corruption"],
    ["Expired session token",     "Middleware returns 401"],
], col_widths=[2.5, 4.0])

h3(doc, "Security Tests")
table(doc, ["Test", "Assertion"], [
    ["OS-level path enforcement",   "Service account cannot write outside allowed tree"],
    ["Clean subprocess env",        "DB credentials and JWT keys absent from script env"],
    ["Atomic write",                "No partial file visible during write"],
    ["Filename sanitization",       "Shell metacharacters in filename do not reach OS"],
    ["No path in error response",   "Errors contain no filesystem paths or stack traces"],
], col_widths=[2.5, 4.0])

h2(doc, "7.5  Cross-Layer Integration Tests")
h3(doc, "Scenario 1 — Happy Path")
code(doc,
"""1. Create vendor; issue enrollment link
2. Simulate app enrollment (call /enroll with device_uuid + enrollment_token)
3. Login: POST /auth/login with username + password + valid TOTP + device_uuid
4. Upload a file to an allowed directory
5. Trigger an allowed script operation
6. Advance clock to 25 minutes; renewal prompt confirmed
7. Submit new TOTP; session resets
8. Logout; session token invalidated
Expected: all steps succeed; audit log contains entries for steps 4, 5, 7, 8""")

h3(doc, "Scenario 2 — Revocation Mid-Session")
code(doc,
"""1. Vendor logs in successfully
2. Admin revokes vendor's device UUID
3. Vendor attempts session renewal → rejected (device revoked)
4. All subsequent portal requests return 401""")

h3(doc, "Scenario 3 — Lockout and Recovery")
code(doc,
"""1. Submit correct password + wrong TOTP 5 times → 401 / 423 after threshold
2. Correct TOTP during lockout → still rejected
3. Advance clock past cooldown; correct TOTP → 200""")

h3(doc, "Scenario 4 — Enrollment Replay")
code(doc,
"""1. Enrollment link used successfully
2. Same link submitted again → 400
3. Device registry contains exactly one device for the vendor""")

table(doc,
    ["Layer", "Unit", "Integration", "Security", "Key Doubles"],
    [
        ["Mobile App",    "TOTP vectors, keychain",   "Local enrollment stub",    "No-leak, no-transmit",      "Fake keychain, stub HTTPS"],
        ["Web Portal",    "Component render, roles",  "MSW contract mock",        "Cookie, XSS, CSRF",         "MSW, headless browser"],
        ["Auth Service",  "JWT, TOTP, lockout",       "In-memory DB",             "Timing, enumeration, keys", "Fake clock, injectable random"],
        ["Backend API",   "Path, op registry",        "Temp filesystem, stubs",   "OS isolation, env leak",    "Temp dir, restricted user"],
        ["Cross-Layer",   "—",                        "All layers + clock",        "Revocation, replay",        "docker-compose test env"],
    ],
    col_widths=[1.4, 1.5, 1.7, 1.6, 1.8]
)
hr(doc)

# ═══════════════════════════════════════════════════════════════════════════════
# 8. AI BUILD PROMPTS
# ═══════════════════════════════════════════════════════════════════════════════
h1(doc, "8. AI Build Prompts")
h2(doc, "8.1  How to Use the Prompts")
body(doc, (
    "The prompts below are designed to be given to an AI coding assistant (Claude, Copilot, Cursor) "
    "in sequence. Each prompt is self-contained but references the outputs of earlier prompts. "
    "Follow the sequencing order. Do not skip a layer."
))
table(doc,
    ["Order", "Prompt", "Output"],
    [
        ["1", "Auth Service & Device Registry", "Running auth service + DB schema + API contract"],
        ["2", "Backend API",                    "File/script API referencing auth service JWT"],
        ["3", "Web Portal SPA",                 "Browser app consuming the Backend API contract"],
        ["4", "Native Mobile App",              "iOS + Android app consuming the Enrollment API"],
        ["5", "Test Harness",                   "Full test suite for all layers"],
        ["6", "Infrastructure & Deployment",    "docker-compose + systemd/NSSM configs"],
    ],
    col_widths=[0.6, 2.5, 3.4]
)
body(doc, "Before starting, set these environment variables in your shell or CI system:")
code(doc,
"""JWT_SIGNING_KEY=<generate: openssl genrsa -out jwt_private.pem 4096>
JWT_PUBLIC_KEY=<derived public key>
DB_URL=postgresql://...   (or sqlite:///./test.db for local dev)
ADMIN_API_KEY=<random 32-byte hex>
ENROLLMENT_LINK_BASE_URL=https://your-portal-host/enroll""")

h2(doc, "8.2  Prompt 1 — Auth Service & Device Registry")
code(doc,
"""Build a standalone authentication service in Python using FastAPI.
The service owns all authentication and device registry logic for a vendor portal.

REQUIREMENTS:

Database (SQLAlchemy + Alembic; SQLite dev / Postgres prod):
  - vendors:            id, username, bcrypt_password_hash, role, created_at, active
  - devices:            id, vendor_id(FK), uuid_hash, totp_seed_hash,
                        enrolled_at, revoked, revoked_at, last_used_at
  - enrollment_tokens:  id, token_hash, vendor_id(FK), expires_at, used, used_at
  - auth_attempts:      id, vendor_id(FK), attempted_at, success, failure_reason

Endpoints:
  POST /auth/login
    Body: { username, password, totp_code, device_uuid }
    - Validate bcrypt password (constant-time)
    - Validate RFC 6238 TOTP (±1 window)
    - Reject replayed codes (cache per 30s window)
    - Check device UUID hash registered and not revoked
    - All failures return { "error": "authentication failed" } — same message always
    - Rate limit: 5 failed attempts per vendor per 10 min → 10-min lockout
    - On success: issue RS256 JWT (claims: vendor_id, role, iat, exp 30min)
    - JWT_SIGNING_KEY from env only — refuse startup if absent

  POST /enroll
    Body: { enrollment_token, device_uuid }
    - Validate token: known, unused, not expired
    - Generate 20-byte cryptographically random TOTP seed
    - Return seed as base32 (once only — never stored in plaintext)
    - Store hash(device_uuid) and hash(totp_seed) in devices table
    - Mark token used in same DB transaction
    - Return { "totp_seed": "<base32>", "enrolled": true }

  POST /auth/validate (internal)
    Body: { jwt_token }
    Returns: { valid, vendor_id, role, expires_at } or 401

  Admin (require ADMIN_API_KEY header):
  POST /admin/vendors           — create vendor, return enrollment link
  POST /admin/devices/revoke    — revoke device UUID hash
  GET  /admin/devices           — list devices for vendor
  POST /admin/enrollment-links  — issue new enrollment link

SECURITY:
  - Constant-time comparisons everywhere (hmac.compare_digest)
  - JWT_SIGNING_KEY, DB_URL, ADMIN_API_KEY from env only; exit(1) if absent
  - No credentials/seeds/keys logged at any level
  - Startup: check all required env vars; log clear error and exit if any absent

TESTS (pytest):
  JWT issuance/validation, TOTP window, replay protection, lockout logic,
  revocation, enrollment single-use, all security checks above.
  Use in-memory SQLite and injectable fake clock for time-sensitive tests.""")

h2(doc, "8.3  Prompt 2 — Backend API (File & Script Operations)")
code(doc,
"""Build a backend API in Python/FastAPI handling file uploads and script execution.
Validates JWTs by calling Auth Service POST /auth/validate.

CONFIG (env vars — refuse startup if absent):
  AUTH_SERVICE_URL, IDMC_STAGING_ROOT, ALLOWED_PATHS_CONFIG,
  OPERATIONS_CONFIG, UPLOAD_TOKEN_SECRET

paths.yaml:
  vendor_standard:  [pm_scripts, source_files, parameter_files]
  vendor_premium:   [pm_scripts, source_files, target_files, parameter_files]

operations.yaml:
  daily_load:       { script: /opt/idmc/scripts/daily_load.sh,    roles: [vendor_standard, vendor_premium] }
  parameter_reload: { script: /opt/idmc/scripts/reload_params.sh, roles: [vendor_premium] }

Endpoints:
  POST /upload/request  (JWT auth)
    Body: { directory, filename }
    - Validate JWT; extract vendor role
    - Check directory in vendor allowlist
    - Sanitize filename (strip path separators, shell metacharacters)
    - Resolve full path; canonicalize; confirm starts with IDMC_STAGING_ROOT
    - Issue signed upload token (scoped to exact path; expires 60min; single-use)

  PUT /upload/{upload_token}
    - Validate/consume token
    - Write to temp file in same directory; atomic rename to final path
    - Log: vendor_id, final_path, file_size, timestamp, outcome
    - Return { "uploaded": true, "path": "<filename only>" }

  POST /operations/run  (JWT auth)
    Body: { operation_name }
    - Validate JWT; check role permits operation
    - Spawn subprocess: [script_path] with CLEAN env only:
      PATH=/usr/bin:/bin, HOME=/tmp, LANG=en_US.UTF-8
    - Capture stdout+stderr; 120-second timeout; kill on timeout
    - Log: vendor_id, operation_name, exit_code, duration_ms, timestamp
    - Return { operation, exit_code, output, duration_ms }

SECURITY:
  - Canonical path check before every write
  - Filename sanitization: strip /, \\, .., metacharacters
  - Subprocess: never pass parent environment
  - Error responses: no filesystem paths or stack traces

TESTS (pytest + temp directory):
  Path validation, traversal attempts (literal + encoded), filename sanitization,
  atomic write, upload token single-use, op registry, forbidden role, clean subprocess env.""")

h2(doc, "8.4  Prompt 3 — Web Portal SPA")
code(doc,
"""Build a React (TypeScript) SPA for the IDMC vendor portal.

Talks to:
  - Auth Service: POST /auth/login, POST /auth/validate
  - Backend API:  POST /upload/request, PUT /upload/{token}, POST /operations/run

PAGES:
1. Login
   - Username + password; on success show 6-digit TOTP input
   - TOTP: exactly 6 numeric digits (client-side validation)
   - Failed login: generic "Login failed" — do not distinguish which factor
   - After 3 TOTP failures: disable form, show lockout countdown

2. Portal Home (authenticated)
   - Fetch role from /auth/validate on load
   - Show only permitted directories and operations
   - Session expiry countdown in header
   - At 5 min remaining: renewal banner → TOTP prompt → /auth/renew → reset timer

3. File Upload View
   - Permitted directory selector
   - Drag-and-drop file picker; reject >500MB client-side before upload
   - POST /upload/request → PUT /upload/{token} with progress bar
   - Show filename (not full path) and timestamp on success

4. Script Operations View
   - Named buttons with descriptions; disable during in-flight operation
   - Spinner + elapsed time; show exit code, truncated output (2000 chars), duration
   - Timeout message if 120s exceeded

SECURITY:
  - No token in localStorage or sessionStorage — HttpOnly cookie only
  - All filenames HTML-escaped before display
  - CSP meta tag: default-src 'self'; script-src 'self'
  - credentials: 'include' on all API calls
  - Login redirect validated against internal path allowlist

TESTS (Vitest + Testing Library):
  Login validation, failed login message, role-based rendering, countdown + renewal,
  upload flow (mock API), XSS filename escaping, script button disabled during run.""")

h2(doc, "8.5  Prompt 4 — Native Mobile App")
code(doc,
"""Build a React Native (Expo managed) app for iOS and Android.
Two functions only: enrollment and TOTP code display.

SCREENS:
1. Enrollment
   - Entry: deep link  idmc-auth://enroll?token=<one_time_token>
   - On open: generate UUID (expo-crypto) → POST to ENROLLMENT_API_URL/enroll
     with { enrollment_token, device_uuid } over pinned TLS
   - On success: store device_uuid + totp_seed in Expo SecureStore
   - Error states: expired token, already used, network error, cert mismatch
   - If already enrolled: offer re-enrollment flow

2. TOTP Code Screen (main)
   - Read seed from SecureStore
   - Generate RFC 6238 TOTP locally (SHA-1, 6 digits, 30s period)
   - Display code in large font + circular countdown to next window
   - Auto-refresh on window rollover
   - Never show raw seed

3. Settings
   - Re-enroll button (clears stored seed + UUID)
   - App version

SECURITY:
  - seed and UUID ONLY in Expo SecureStore (hardware-backed)
  - Neither value in console logs, crash reports, or AsyncStorage
  - TLS cert pin hash in bundled config file (not hardcoded in JS)
  - No unnecessary permissions (no camera, contacts, location)
  - Deep link validates token present + non-empty before any network call

TESTS (Jest + RNTL):
  TOTP vectors, 30s rollover (fake timers), deep link extraction,
  expired/missing token error, SecureStore mock, cert mismatch abort,
  seed/UUID absent from all console.log output.""")

h2(doc, "8.6  Prompt 5 — Test Harness")
code(doc,
"""Set up the complete test harness across all four components.

TASK 1 — Python conftest.py (root level):
  - fake_clock: injectable datetime replacing datetime.now() in all services
  - in_memory_db: fresh SQLite DB with Alembic migrations applied
  - rfc6238_vectors: the 6 official RFC 6238 test vectors as pytest params
  - temp_idmc_dir: temp directory mirroring production IDMC path structure;
    torn down after each test
  - Confirm all tests have zero real filesystem side-effects
  - Test that service account cannot write outside temp_idmc_dir (OS-level check)

TASK 2 — Cross-layer scenarios (pytest + httpx; spin up via docker-compose):
  Scenario 1 — Happy Path (steps as described in Section 7.5)
  Scenario 2 — Revocation Mid-Session
  Scenario 3 — Lockout and Recovery
  Scenario 4 — Enrollment Replay
  Use docker-compose.test.yml with SQLite, MailHog SMTP sink, controllable clock.

TASK 3 — Frontend (portal-spa/):
  - MSW handlers for all API endpoints (importable as fixtures)
  - renderWithProviders(component): wraps with router + auth context
  - createMockVendor(role): returns mock auth state for a given role

TASK 4 — Mobile (mobile-app/):
  - mockSecureStore: intercepts expo-secure-store; stores values in memory
  - mockFetch: configurable success/error/cert-mismatch responses
  - rfc6238Vectors: 6 official TOTP test vectors""")

h2(doc, "8.7  Prompt 6 — Infrastructure & Deployment")
code(doc,
"""Create deployment configuration for Windows Server 2019+ and Ubuntu 22.04+.

TASK 1 — docker-compose.yml:
  - auth-service (Python 3.12 slim), backend-api (Python 3.12 slim),
    postgres, nginx (self-signed cert for local dev)
  - Secrets via environment variables only — never baked into images
  - Healthcheck per service
  - auth-service + backend-api on internal network; only nginx port 443 exposed
  docker-compose.test.yml (extends base):
  - SQLite substituted for Postgres
  - MailHog for enrollment email testing
  - IDMC_STAGING_ROOT on temp volume

TASK 2 — Linux systemd units:
  - User=idmc-portal (least-privilege; no sudo)
  - EnvironmentFile=/etc/idmc-portal/<service>.env (mode 0640, owned root:idmc-portal)
  - NoNewPrivileges, ProtectSystem=strict, PrivateTmp, ReadWritePaths for staging only
  install.sh: create service account, set permissions, install + enable units

TASK 3 — Windows NSSM (install-windows.ps1):
  - Install NSSM; create local idmc-portal service account (no login rights)
  - Register both services; store secrets via Windows DPAPI
  - IDMC_STAGING_ROOT ACL: idmc-portal Modify; no other standard user Write
  - Auto-start + start services

TASK 4 — nginx.conf:
  - TLS 1.2 min / TLS 1.3 preferred; HSTS; CSP; X-Frame-Options: DENY
  - Rate limit: 20 req/s per IP, burst 50
  - Max body: 550MB; proxy to backend-api only (auth-service has no nginx route)
  - Access log: JSON with timestamp, client_ip, method, uri, status, bytes, response_time_ms

TASK 5 — Secrets template:
  - .env.template (committed; no real values)
  - generate-secrets.sh: uses openssl rand; outputs ready-to-paste env blocks""")
hr(doc)

# ═══════════════════════════════════════════════════════════════════════════════
# 9. DEPLOYMENT & OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════
h1(doc, "9. Deployment & Operations")
h2(doc, "9.1  Runtime Requirements")
table(doc,
    ["Component", "Windows", "Linux"],
    [
        ["Auth Service",          "Python 3.12, NSSM, Windows DPAPI",     "Python 3.12, systemd, secret-service"],
        ["Backend API",           "Python 3.12, NSSM",                     "Python 3.12, systemd"],
        ["Reverse Proxy",         "nginx for Windows or Caddy",            "nginx or Caddy"],
        ["Database",              "PostgreSQL 15+ or SQLite",              "PostgreSQL 15+ or SQLite"],
        ["Mobile distribution",   "Enterprise MDM or direct APK/IPA",     "Enterprise MDM or direct APK/IPA"],
    ],
    col_widths=[1.8, 2.5, 2.5]
)

h2(doc, "9.2  Secret Rotation")
table(doc,
    ["Secret", "Rotation Procedure"],
    [
        ["JWT signing key",     "Generate new RS256 pair; deploy public key to backend-api; deploy private key to auth-service; both accept old tokens until hard expiry (30 min overlap)"],
        ["Admin API key",       "Generate new key; update env file; restart auth-service; no overlap needed"],
        ["TOTP seeds",          "No rotation — bound to device enrollment; rotate via revoke + new enrollment link"],
        ["DB credentials",      "Update DB password; update DB_URL env var; restart both services"],
        ["TLS certificate",     "Replace cert on nginx; update cert pin hash in mobile app bundle; redistribute app"],
    ],
    col_widths=[1.6, 5.0]
)

h2(doc, "9.3  Audit Log Fields")
table(doc,
    ["Event", "Logged Fields"],
    [
        ["Login success",      "vendor_id, device_uuid_hash, timestamp, source_ip, session_id"],
        ["Login failure",      "username_hash, failure_type (generic), timestamp, source_ip, attempt_count"],
        ["File upload",        "vendor_id, session_id, directory, filename, file_size_bytes, timestamp, outcome"],
        ["Script execution",   "vendor_id, session_id, operation_name, exit_code, duration_ms, timestamp"],
        ["Session renewal",    "vendor_id, session_id, timestamp, new_expiry"],
        ["Device revocation",  "admin_id, device_uuid_hash, vendor_id, timestamp"],
        ["Enrollment",         "vendor_id, device_uuid_hash, timestamp, enrollment_token_hash"],
    ],
    col_widths=[1.6, 4.9]
)
hr(doc)

# ═══════════════════════════════════════════════════════════════════════════════
# 10. ENVIRONMENT VARIABLES — COMPLETE GUIDE
# ═══════════════════════════════════════════════════════════════════════════════
h1(doc, "10. Environment Variables — Complete Guide")
body(doc, (
    "There are four distinct concerns: what the variables are, how to generate their values, "
    "where to store them securely on each OS, and how the services read them at runtime. "
    "This section covers each in full."
))

h2(doc, "10.1  Full Variable List")
table(doc,
    ["Variable", "Used By", "What It Is"],
    [
        ["JWT_SIGNING_KEY (or _PATH)", "Auth Service",  "RS256 private key (PEM) for signing session tokens"],
        ["JWT_PUBLIC_KEY (or _PATH)",  "Backend API",   "RS256 public key for verifying tokens — never the private key"],
        ["DB_URL",                     "Auth Service",  "Full database connection string including credentials"],
        ["ADMIN_API_KEY",              "Auth Service",  "Random secret required on all admin endpoint calls"],
        ["UPLOAD_TOKEN_SECRET",        "Backend API",   "Random secret for signing scoped upload tokens"],
        ["AUTH_SERVICE_URL",           "Backend API",   "Internal URL of the Auth Service (not a secret, but env-controlled)"],
        ["IDMC_STAGING_ROOT",          "Backend API",   "Absolute path to the root of all IDMC staging directories"],
        ["ALLOWED_PATHS_CONFIG",       "Backend API",   "Path to YAML file: role → allowed subdirectory list"],
        ["OPERATIONS_CONFIG",          "Backend API",   "Path to YAML file: operation name → absolute script path"],
        ["ENROLLMENT_LINK_BASE_URL",   "Auth Service",  "Base URL prepended to one-time enrollment links sent to vendors"],
        ["SMTP_URL",                   "Auth Service",  "Connection string for mail server sending enrollment links"],
    ],
    col_widths=[2.2, 1.5, 2.8]
)

h2(doc, "10.2  Step 1 — Generate Each Secret")
body(doc, (
    "Every secret must be generated with a cryptographically secure random source. "
    "Never invent values by hand and never reuse values across environments."
))

h3(doc, "JWT RS256 Key Pair")
body(doc, (
    "The private key signs tokens. The public key verifies them. They are generated together "
    "once and kept permanently separated — the Backend API only ever receives the public key."
))
code(doc,
"""# Generate 4096-bit RSA private key
openssl genrsa -out jwt_private.pem 4096

# Derive the matching public key
openssl rsa -in jwt_private.pem -pubout -out jwt_public.pem

# Lock down permissions immediately
chmod 600 jwt_private.pem
chmod 644 jwt_public.pem""")
body(doc, (
    "PEM files contain newlines. Storing a multi-line value directly in an env var is error-prone. "
    "The recommended pattern is to store the file path in the variable and have the service read "
    "the file at startup:"
))
code(doc,
"""JWT_SIGNING_KEY_PATH=/etc/idmc-portal/jwt_private.pem
JWT_PUBLIC_KEY_PATH=/etc/idmc-portal/jwt_public.pem""")
body(doc, "If your deployment requires the PEM content inline (e.g., a cloud secret manager), use this to convert it to a single-line value with literal \\n markers:")
code(doc,
"""# Linux / macOS
export JWT_SIGNING_KEY=$(awk 'NF {sub(/\\r/, ""); printf "%s\\\\n",$0;}' jwt_private.pem)""")

h3(doc, "Random Hex Secrets (Admin API Key, Upload Token Secret)")
code(doc,
"""# 32 bytes = 256-bit entropy, hex-encoded (64 characters)
openssl rand -hex 32

# Run once per secret — do not share values between variables
ADMIN_API_KEY=$(openssl rand -hex 32)
UPLOAD_TOKEN_SECRET=$(openssl rand -hex 32)""")

h3(doc, "Database Password and URL")
code(doc,
"""# Generate a strong database password
DB_PASSWORD=$(openssl rand -hex 24)   # 48-character hex string

# PostgreSQL connection string
DB_URL=postgresql://idmc_user:${DB_PASSWORD}@localhost:5432/idmc_portal

# SQLite (dev / single-host only — no network credentials needed)
DB_URL=sqlite:////opt/idmc-portal/idmc_portal.db""")

h2(doc, "10.3  Step 2 — Store Secrets Securely (Linux)")
body(doc, (
    "The core rule: the plaintext value must never exist in a file readable by anyone "
    "other than the service account."
))

h3(doc, "Approach A — EnvironmentFile (recommended for single-host)")
body(doc, "Create a directory and file owned by the service account with no world-read permission:")
code(doc,
"""# Create directory
sudo mkdir -p /etc/idmc-portal
sudo chown root:idmc-portal /etc/idmc-portal
sudo chmod 750 /etc/idmc-portal

# Create the environment file
sudo touch /etc/idmc-portal/auth-service.env
sudo chown root:idmc-portal /etc/idmc-portal/auth-service.env
sudo chmod 640 /etc/idmc-portal/auth-service.env
# Result: owner (root) can read/write; group (idmc-portal) can read; others: no access""")
body(doc, "Populate the file as root (nano, vim, or heredoc):")
code(doc,
"""sudo tee /etc/idmc-portal/auth-service.env > /dev/null << 'EOF'
JWT_SIGNING_KEY_PATH=/etc/idmc-portal/jwt_private.pem
DB_URL=postgresql://idmc_user:REPLACE_PASSWORD@localhost:5432/idmc_portal
ADMIN_API_KEY=REPLACE_WITH_GENERATED_HEX
ENROLLMENT_LINK_BASE_URL=https://portal.yourcompany.com/enroll
SMTP_URL=smtp://relay.yourcompany.com:587
EOF""")
body(doc, "The systemd unit file references this with a single directive:")
code(doc,
"""[Service]
User=idmc-portal
EnvironmentFile=/etc/idmc-portal/auth-service.env""")
body(doc, "The service reads variables as normal environment variables — no application code change needed.")

h3(doc, "Approach B — systemd Credentials (encrypted at rest, systemd 249+)")
body(doc, "systemd can encrypt secrets using the machine's TPM or host key. The plaintext never touches the filesystem unencrypted:")
code(doc,
"""# Encrypt and store a secret
sudo systemd-creds encrypt --name=db-url - /etc/credstore/db-url.cred
# (paste the DB URL at the prompt, then press Ctrl+D)

# Set correct permissions on the credential store
sudo chmod 600 /etc/credstore/db-url.cred""")
code(doc,
"""# In the systemd unit file
[Service]
LoadCredential=db-url:/etc/credstore/db-url.cred""")
body(doc, "The service reads the decrypted value from the path $CREDENTIALS_DIRECTORY/db-url at runtime. This approach is the right choice when the host is shared or compliance requires encrypted-at-rest secrets.")

h2(doc, "10.4  Step 2 — Store Secrets Securely (Windows)")

h3(doc, "Approach A — NSSM Per-Service Environment Variables")
body(doc, "NSSM stores per-service environment variables in the Windows registry under the service key. They are not visible to other users in Task Manager or standard environment introspection.")
code(doc,
"""# Set each variable during service installation
nssm set idmc-auth-service AppEnvironmentExtra `
    "JWT_SIGNING_KEY_PATH=C:\\idmc-portal\\certs\\jwt_private.pem" `
    "DB_URL=postgresql://idmc_user:password@localhost:5432/idmc_portal" `
    "ADMIN_API_KEY=<generated hex>"

# Restrict the registry key so only SYSTEM and idmc-portal can read it
$acl = Get-Acl "HKLM:\\SYSTEM\\CurrentControlSet\\Services\\idmc-auth-service"
# (apply ACL restricting to SYSTEM + idmc-portal only)""")

h3(doc, "Approach B — Windows DPAPI Encrypted Credential Files")
body(doc, "Windows Data Protection API (DPAPI) encrypts data using a key derived from the machine account. Only the same machine (and service account) can decrypt it. Nothing travels in plaintext on disk.")
code(doc,
"""# PowerShell: encrypt and save a secret
$secret   = "postgresql://idmc_user:password@localhost:5432/idmc_portal"
$bytes    = [System.Text.Encoding]::UTF8.GetBytes($secret)
$encrypted = [System.Security.Cryptography.ProtectedData]::Protect(
    $bytes,
    $null,
    [System.Security.Cryptography.DataProtectionScope]::LocalMachine
)
[System.IO.File]::WriteAllBytes(
    "C:\\idmc-portal\\secrets\\db_url.dpapi",
    $encrypted
)""")
body(doc, "The service reads and decrypts at startup using the matching Unprotect call. The plaintext string is only ever held in memory during the service's lifetime.")
body(doc, "For a first deployment, NSSM environment variables with tight ACLs is the pragmatic choice. DPAPI is the right step up when the host is shared or compliance requires encrypted-at-rest secrets.")

h2(doc, "10.5  Step 3 — What Never To Do")
table(doc,
    ["What", "Why It Is Dangerous"],
    [
        ["export SECRET=value in a committed shell script",              "Git history is permanent; the secret is exposed to everyone with repo access — including forks and future contributors"],
        ["os.getenv('JWT_KEY', 'dev-secret') fallback defaults",        "The fallback value silently becomes the production value when the real env var is accidentally unset"],
        ["Secrets in docker-compose.yml under environment:",            "docker-compose files are typically committed to version control and visible in CI logs"],
        ["Printing env vars in startup logs for debugging",             "Log files are often less protected than secret stores and may be shipped to log aggregators"],
        ["Same secret values across dev / staging / prod",             "A breach of any lower environment immediately exposes production"],
        ["Storing private key and public key on the same service",      "The Backend API only needs the public key; giving it the private key violates least privilege and widens blast radius"],
        ["Secrets in container image layers (ENV in Dockerfile)",       "Image layers are inspectable by anyone who can pull the image; secrets baked in cannot be rotated without rebuilding"],
        ["Secrets in Kubernetes ConfigMaps (not Secrets)",             "ConfigMaps are not encrypted at rest by default and are readable by all pods in the namespace"],
    ],
    col_widths=[2.8, 3.7]
)

h2(doc, "10.6  Step 4 — How Services Read Variables at Runtime")
body(doc, (
    "The service must enforce that every required variable is present at startup and exit "
    "immediately with a clear error if any are missing. This prevents a misconfigured deployment "
    "from running in a degraded or insecure state."
))
code(doc,
"""import os, sys

REQUIRED = [
    "JWT_SIGNING_KEY_PATH",
    "DB_URL",
    "ADMIN_API_KEY",
    "ENROLLMENT_LINK_BASE_URL",
    "SMTP_URL",
]

def check_env():
    missing = [v for v in REQUIRED if not os.getenv(v)]
    if missing:
        for v in missing:
            print(f"ERROR: required env var '{v}' is not set", file=sys.stderr)
        sys.exit(1)

# Called before the application starts accepting connections
check_env()""")
body(doc, "For variables that point to files (key paths, config paths), add an additional existence check:")
code(doc,
"""def check_file_vars():
    file_vars = ["JWT_SIGNING_KEY_PATH", "JWT_PUBLIC_KEY_PATH",
                 "ALLOWED_PATHS_CONFIG", "OPERATIONS_CONFIG"]
    for var in file_vars:
        path = os.getenv(var)
        if path and not os.path.isfile(path):
            print(f"ERROR: {var}='{path}' does not exist or is not a file", file=sys.stderr)
            sys.exit(1)""")
body(doc, "These checks run before the application starts accepting connections. Errors go to stderr, captured by systemd or NSSM logs — never to an HTTP response.")

h2(doc, "10.7  Step 5 — Per-Environment Strategy")
body(doc, "Each environment gets its own completely independent set of generated secrets.")
table(doc,
    ["Environment", "Database", "Secret Storage", "Who Generates Secrets"],
    [
        ["Local dev",   "SQLite",      "Plain .env file, git-ignored",                              "Each developer runs generate-secrets.sh"],
        ["Staging",     "PostgreSQL",  "EnvironmentFile (Linux) or NSSM env vars (Windows)",        "CI/CD pipeline generates on first deploy"],
        ["Production",  "PostgreSQL",  "EnvironmentFile with strict ACL, or DPAPI, or Vault",       "Platform/ops team; secrets never leave the host"],
    ],
    col_widths=[1.4, 1.3, 2.7, 2.1]
)
body(doc, (
    "The repository contains only .env.template (variable names, no values) and generate-secrets.sh. "
    "Neither file ever contains real values. CI/CD pipelines inject secrets via the platform's "
    "native secret injection mechanism (GitHub Secrets, GitLab CI Variables, Azure Key Vault, etc.)."
))

h2(doc, "10.8  generate-secrets.sh")
body(doc, "Run this script to produce a ready-to-paste environment block for any environment. It does not write files — the operator pastes the output into the appropriate secret store.")
code(doc,
"""#!/usr/bin/env bash
set -euo pipefail

echo "========================================="
echo " IDMC Vendor Portal — Secret Generator"
echo " Run once per environment. Paste output"
echo " into your secret store. Do NOT commit."
echo "========================================="
echo ""
echo "=== Auth Service (.env or EnvironmentFile) ==="
echo "JWT_SIGNING_KEY_PATH=/etc/idmc-portal/jwt_private.pem"
echo "JWT_PUBLIC_KEY_PATH=/etc/idmc-portal/jwt_public.pem"
echo "ADMIN_API_KEY=$(openssl rand -hex 32)"
echo "DB_URL=postgresql://idmc_user:$(openssl rand -hex 24)@localhost:5432/idmc_portal"
echo "ENROLLMENT_LINK_BASE_URL=https://REPLACE_WITH_YOUR_HOST/enroll"
echo "SMTP_URL=smtp://REPLACE_WITH_YOUR_RELAY:587"
echo ""
echo "=== Backend API (.env or EnvironmentFile) ==="
echo "JWT_PUBLIC_KEY_PATH=/etc/idmc-portal/jwt_public.pem"
echo "UPLOAD_TOKEN_SECRET=$(openssl rand -hex 32)"
echo "AUTH_SERVICE_URL=http://127.0.0.1:8001"
echo "IDMC_STAGING_ROOT=/opt/idmc/staging"
echo "ALLOWED_PATHS_CONFIG=/etc/idmc-portal/paths.yaml"
echo "OPERATIONS_CONFIG=/etc/idmc-portal/operations.yaml"
echo ""
echo "=== Key Pair Generation Commands (run separately as root) ==="
echo "openssl genrsa -out /etc/idmc-portal/jwt_private.pem 4096"
echo "openssl rsa -in /etc/idmc-portal/jwt_private.pem -pubout \\"
echo "    -out /etc/idmc-portal/jwt_public.pem"
echo "chmod 640 /etc/idmc-portal/jwt_private.pem /etc/idmc-portal/jwt_public.pem"
echo "chown root:idmc-portal /etc/idmc-portal/jwt_private.pem \\"
echo "    /etc/idmc-portal/jwt_public.pem" """)

h2(doc, "10.9  Summary Decision Tree")
code(doc,
"""Is the host shared with other applications or teams?
├── No  → EnvironmentFile (Linux) or NSSM env vars (Windows) with tight ACL
│         Simple, auditable, no extra dependencies
│
└── Yes → systemd credentials + TPM (Linux) or DPAPI (Windows)
          Encrypted at rest; other processes on the same host cannot read them

Is this a cloud deployment?
└── Yes → Use the cloud provider's native secret manager
          AWS Secrets Manager / Azure Key Vault / GCP Secret Manager
          Inject at container or VM startup via IAM role — no env files at all
          The service account's IAM role is the access control; no passwords

Do you need secret rotation without redeploying the app?
└── Yes → HashiCorp Vault with dynamic secrets
          Vault issues short-lived DB credentials and renews them automatically
          The service holds a Vault token; Vault manages rotation transparently""")
hr(doc)

# ═══════════════════════════════════════════════════════════════════════════════
# 11. OPEN QUESTIONS & FUTURE ENHANCEMENTS
# ═══════════════════════════════════════════════════════════════════════════════
h1(doc, "11. Open Questions & Future Enhancements")
h2(doc, "11.1  Open Questions")
table(doc,
    ["Question", "Impact", "Owner"],
    [
        ["Maximum file size per upload?",                             "nginx body size limit and upload token TTL",         "Platform team"],
        ["Which IDMC directories are in scope at launch?",           "Drives paths.yaml initial content",                  "Informatica admin"],
        ["What is the approved script list at launch?",              "Drives operations.yaml initial content",             "Informatica admin"],
        ["Enrollment emails via internal SMTP relay or external?",   "docker-compose and deployment config",               "Infrastructure"],
        ["PostgreSQL on Secure Agent host or SQLite sufficient?",    "DB driver and migration config",                     "Platform team"],
        ["Mobile app distribution — MDM, TestFlight, or direct APK?","Code signing and Expo build pipeline",              "Mobile/DevOps"],
    ],
    col_widths=[2.5, 2.0, 1.5]
)

h2(doc, "11.2  Potential Future Enhancements")
bul(doc, "SAML / OIDC SSO — replace username/password first factor with enterprise IdP")
bul(doc, "Push notification OTP approval — vendor approves a push notification instead of reading a code")
bul(doc, "Vendor self-service device re-enrollment with identity verification step")
bul(doc, "Admin web UI for device registry management (currently admin API only)")
bul(doc, "File integrity verification — vendor provides a checksum; server validates before accepting")
bul(doc, "Configurable per-vendor upload quotas (daily MB limit, file count limit)")
bul(doc, "IDMC run-status webhooks — show live IDMC job status in the portal after script trigger")
bul(doc, "HashiCorp Vault integration for automatic secret rotation without service restarts")

doc.add_paragraph()
hr(doc)
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("End of Document  —  IDMC Vendor File Portal Design v1.1  —  May 2026")
run.font.size = Pt(9)
run.font.color.rgb = GREY_TEXT

# ── Save ──────────────────────────────────────────────────────────────────────
out = "/Users/amr.osman/Documents/Informatica/Research/code/Customer-Click-Data Transfer/IDMC_Vendor_Portal_Design_v1.1.docx"
doc.save(out)
print(f"Saved: {out}")
