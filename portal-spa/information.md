how to use and how to run the tests                                                                  

  Thought for 2s (ctrl+o to expand)

⏺ Using the Portal SPA

  1. Prerequisites

  Node.js 18+ must be installed. Check with:
  node --version
  npm --version
  
  If not installed, download from https://nodejs.org or via Homebrew:
  brew install node
  
  ---
  2. Install dependencies

  cd "portal-spa"
  npm install

  ---
  3. Start the dev server
  
  The backend services must be running first (auth-service on 8001, backend-api on 8002).

  # Terminal 1 — auth service
  cd auth-service && source .venv/bin/activate
  uvicorn app.main:app --port 8001

  # Terminal 2 — backend API
  cd backend-api && source .venv/bin/activate
  uvicorn app.main:app --port 8002

  # Terminal 3 — portal SPA
  cd portal-spa
  npm run dev
  # Opens at http://localhost:5173

  Vite proxies /auth/* → 8001 and /upload/*, /operations/* → 8002 automatically, so there are no CORS
  issues in development.

  ---
  4. Typical vendor workflow in the browser
  
  1. Go to http://localhost:5173
  2. Enter username + password → click Sign in
  3. Enter the 6-digit code from the mobile app → click Verify
  4. Portal loads showing your permitted directories and operations
  5. Select a directory, drop a file, click Upload
  6. Or go to Script Operations and click Run on a permitted operation
  7. Session countdown shown in the header — renew at the 5-minute warning

  ---
  5. Build for production

  npm run build
  # Output: dist/
  # Serve dist/ with nginx or any static file server

  ---
  Running the tests
  
  cd "portal-spa"
  npm test

  Useful variations

  # Watch mode (re-runs on file save)
  npm run test:watch

  # With coverage report
  npm run test:coverage

  # One file
  npx vitest run src/__tests__/LoginPage.test.tsx

  # By test name pattern
  npx vitest run -t "lockout"
  npx vitest run -t "XSS"

  ---
  Expected output

   ✓ src/__tests__/utils.test.ts (12 tests)
   ✓ src/__tests__/LoginPage.test.tsx (12 tests)
   ✓ src/__tests__/FileUploadView.test.tsx (7 tests)
   ✓ src/__tests__/ScriptOperationsView.test.tsx (9 tests)
   ✓ src/__tests__/SessionHeader.test.tsx (8 tests)

   Test Files  5 passed
   Tests       48 passed

  ---
  What each test file covers
  
  ┌───────────────────────────────┬─────────────────────────────────────────────────────────────────┐
  │             File              │                          What it tests                          │
  ├───────────────────────────────┼─────────────────────────────────────────────────────────────────┤
  │ utils.test.ts                 │ escapeHtml escapes < > & " '; redirect allowlist blocks         │
  │                               │ external URLs                                                   │
  ├───────────────────────────────┼─────────────────────────────────────────────────────────────────┤
  │ LoginPage.test.tsx            │ TOTP field strips non-digits; generic error message; lockout    │
  │                               │ after 3 failures; nothing written to localStorage               │
  ├───────────────────────────────┼─────────────────────────────────────────────────────────────────┤
  │                               │ Only permitted dirs shown; 500 MB client guard fires before     │
  │ FileUploadView.test.tsx       │ fetch; upload success shows filename only; XSS filename         │
  │                               │ rendered as text not HTML                                       │
  ├───────────────────────────────┼─────────────────────────────────────────────────────────────────┤
  │                               │ Run button disabled while in-flight; elapsed timer ticks;       │
  │ ScriptOperationsView.test.tsx │ output truncated to 2000 chars; timeout shows message;          │
  │                               │ role-based ops                                                  │
  ├───────────────────────────────┼─────────────────────────────────────────────────────────────────┤
  │ SessionHeader.test.tsx        │ Countdown format correct; renewal banner appears at 5 min;      │
  │                               │ dismiss calls handler; successful renewal updates expiry        │
  └───────────────────────────────┴─────────────────────────────────────────────────────────────────┘

  ---
  Note on the XSS test
  
  This is the most important security test — it verifies that a filename like
  <script>alert(1)</script>.py is rendered as escaped text in the DOM, not as an executable element:

  // FileUploadView.tsx — React renders this as a text node, not HTML
  <span data-testid="selected-filename">{file.name}</span>

  The test confirms el.innerHTML does not contain <script> while el.textContent does — meaning React
  correctly escaped it.


**Task #4**
how to use and how to run tests                                                                      

  Thought for 6s (ctrl+o to expand)

⏺ Using the Admin UI

  1. Start all services

  # Terminal 1 — auth service
  cd "auth-service" && source .venv/bin/activate
  uvicorn app.main:app --port 8001

  # Terminal 2 — backend API
  cd "backend-api" && source .venv/bin/activate
  uvicorn app.main:app --port 8002

  # Terminal 3 — portal SPA
  cd "portal-spa"
  npm run dev
  # Opens at http://localhost:5173

  ---
  2. Create the first admin account
  
  The auth service has no bootstrap endpoint — seed it once with the script from earlier:

  cd "auth-service" && source .venv/bin/activate
  python seed_admin.py   # creates username: sysadmin / password: changeme!

  ---
  3. Admin login
  
  http://localhost:5173/admin/login

  - Enter username and password — no TOTP field, no mobile app needed
  - On success: redirected to /admin/dashboard
  - The admin_session HttpOnly cookie is set by the server — nothing is stored in the browser

  ---
  4. What each page does
  
  ┌────────────────────────────┬────────────────────────────────────────────────────────────────────┐
  │            URL             │                              Purpose                               │
  ├────────────────────────────┼────────────────────────────────────────────────────────────────────┤
  │ /admin/dashboard           │ Stats cards + recent audit events, auto-refreshes every 30s        │
  ├────────────────────────────┼────────────────────────────────────────────────────────────────────┤
  │ /admin/vendors             │ Create vendors (returns enrollment link), deactivate vendors       │
  ├────────────────────────────┼────────────────────────────────────────────────────────────────────┤
  │ /admin/vendors/:id/devices │ Devices for one specific vendor                                    │
  ├────────────────────────────┼────────────────────────────────────────────────────────────────────┤
  │ /admin/devices             │ All devices across all vendors, filter by vendor dropdown          │
  ├────────────────────────────┼────────────────────────────────────────────────────────────────────┤
  │ /admin/audit               │ Filterable audit log — vendor, event type, date range; CSV export  │
  ├────────────────────────────┼────────────────────────────────────────────────────────────────────┤
  │ /admin/sessions            │ Live active sessions, auto-refreshes every 15s, force-expire any   │
  │                            │ session                                                            │
  └────────────────────────────┴────────────────────────────────────────────────────────────────────┘

  ---
  5. Common admin tasks
  
  Create a vendor and get their enrollment link:
  /admin/vendors → "Create Vendor" → fill username, password, role → submit
  → copy-to-clipboard dialog appears with the enrollment link 
  → send the link to the vendor for mobile app setup
  
  Revoke a compromised device:
  /admin/devices → find the device → "Revoke" → confirm dialog → confirmed
  
  Deactivate a vendor immediately:
  /admin/vendors → find the vendor → "Deactivate" → confirm dialog
  → all their devices revoked + all sessions invalidated in one action
  
  Export audit log:
  /admin/audit → set filters → "Export CSV" → file downloads automatically
  
  Force-expire a suspicious session:
  /admin/sessions → find the session → "Force Expire" → confirm dialog
  → row disappears; that session returns 401 on the next request
  
  ---
  6. Security properties
  
  - The vendor portal (/) and admin portal (/admin/*) share no auth state — separate React contexts,
  separate cookies
  - Typing a vendor's session cookie into admin routes returns 403
  - Every destructive action (deactivate, revoke, force-expire) requires a confirmation dialog
  - Audit log is read-only — no edit or delete controls exist in the UI

  ---
  Running the tests
  
  cd "portal-spa"
  npm test

  ---
  Useful variations
  
  # Watch mode
  npm run test:watch

  # Coverage report
  npm run test:coverage

  # Admin tests only
  npx vitest run src/__tests__/admin/

  # One admin file
  npx vitest run src/__tests__/admin/VendorManagement.test.tsx

  # By test name pattern
  npx vitest run -t "deactivate"
  npx vitest run -t "CSV"
  npx vitest run -t "force expire"

  ---
  Expected output

  ✓ src/__tests__/utils.test.ts                       (9)
  ✓ src/__tests__/LoginPage.test.tsx                 (11)
  ✓ src/__tests__/FileUploadView.test.tsx             (7)
  ✓ src/__tests__/ScriptOperationsView.test.tsx       (9)
  ✓ src/__tests__/SessionHeader.test.tsx              (9)
  ✓ src/__tests__/admin/AdminLoginPage.test.tsx       (7)
  ✓ src/__tests__/admin/AdminGuard.test.tsx           (3)
  ✓ src/__tests__/admin/VendorManagement.test.tsx     (8)
  ✓ src/__tests__/admin/DeviceRegistry.test.tsx       (7)
  ✓ src/__tests__/admin/AuditLogViewer.test.tsx       (6)
  ✓ src/__tests__/admin/SessionOverview.test.tsx      (5)

  Test Files  11 passed
  Tests       80 passed
  Duration    ~3s

  ---
  What each admin test file covers

  ┌───────────────────────────┬─────────────────────────────────────────────────────────────────────┐
  │           File            │                            What it tests                            │
  ├───────────────────────────┼─────────────────────────────────────────────────────────────────────┤
  │ AdminLoginPage.test.tsx   │ No TOTP field; generic error message; lockout warning; redirect on  │
  │                           │ success; nothing in localStorage; 403 rejected                      │
  ├───────────────────────────┼─────────────────────────────────────────────────────────────────────┤
  │ AdminGuard.test.tsx       │ Protected content shown when authenticated; redirect to             │
  │                           │ /admin/login when not; page content hidden during redirect          │
  ├───────────────────────────┼─────────────────────────────────────────────────────────────────────┤
  │                           │ Vendor rows render; create form submits and shows enrollment link   │
  │ VendorManagement.test.tsx │ dialog; deactivate shows confirm dialog; cancel prevents API call;  │
  │                           │ row marked inactive after confirmation                              │
  ├───────────────────────────┼─────────────────────────────────────────────────────────────────────┤
  │                           │ Device status shown; no revoke button for already-revoked; revoke   │
  │ DeviceRegistry.test.tsx   │ shows confirm; row updated after confirmation; re-issue shows copy  │
  │                           │ dialog with link                                                    │
  ├───────────────────────────┼─────────────────────────────────────────────────────────────────────┤
  │ AuditLogViewer.test.tsx   │ Rows render; vendor/event-type/date filters update URL and API      │
  │                           │ call; CSV export triggers file download                             │
  ├───────────────────────────┼─────────────────────────────────────────────────────────────────────┤
  │                           │ Session rows render; auto-refresh calls API after 15s (fake         │
  │ SessionOverview.test.tsx  │ timers); force-expire shows confirm dialog; row removed after       │
  │                           │ confirmation; cancel prevents API call                              │
  └───────────────────────────┴─────────────────────────────────────────────────────────────────────┘
  
✻ Cooked for 29s

───────────────────────────────────────────────────────────────────────────────────────────────────────
❯  
───────────────────────────────────────────────────────────────────────────────────────────────────────
  ⏵⏵ accept edits on (shift+tab to cycle) · ← for agents                            100% context used

