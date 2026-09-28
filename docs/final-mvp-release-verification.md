# Final MVP verification — 8 September 2026

Device: `22b01c1e` (Android 24066PC95I). API: `http://192.168.0.107:5000/api`.
The user approved this address for both verification and the APK after DHCP assigned the laptop `.107` and the phone `.108`.

## Requested checks

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Task and appointment workflow | PASS | Admin assigned task 6; executive phone UI moved Pending → In Progress → Completed. Admin read back three history/activity entries and server timestamps. Appointment 5 was created and edited in the phone UI; upcoming API and the dashboard's earliest-three preview agreed. |
| 2 | HR/Admin creates and publishes payroll | PASS | HR authenticated API calls from the phone created a draft, updated it and published payroll 4; Admin read back published=true and net salary 12445.67. |
| 3 | Executive sees only own published payroll | PASS | Draft excluded before publication. Published payroll 4 displayed in the executive phone UI; every returned payroll row belonged to employee 4 and was published. No create/edit controls shown. |
| 4 | Another employee's payroll denied | PASS | Admin verified foreign payroll 1 exists; executive request from phone returned 403. |
| 5 | Executive creates ERP draft/order | PASS | Executive phone UI created order 2 with quantity 2; API confirmed Draft, executive ownership and server product pricing. |
| 6 | Manager/Admin views and confirms ERP | PASS | Manager authenticated API call from phone confirmed order 2; Admin independently read Confirmed. Executive confirmation returned 403. |
| 7 | Another executive's ERP data denied | PASS | Admin verified foreign order 1 exists; executive request from phone returned 403. Own order list contained only owned records. Backend tests also reject query-based ownership spoofing. |
| 8 | Logout revokes token | PASS | Phone UI logout returned to login; reusing the old JWT against /auth/me returned 401. |
| 9 | Deactivated account rejected | PASS | Isolated user 5 received a JWT before deactivation. Phone requests with that token returned 403; its correct login credentials returned 401. Existing accounts were not deactivated. |
| 10 | Login, Attendance/GPS and Client/Camera | PASS | API and UI login passed. Fresh real-GPS check-in/out persisted attendance 3. User captured and confirmed native-camera photo; client 4 saved with GPS and photo 3, whose JPEG was downloaded successfully. |

Executive workflows used Flutter UI on the real phone. Privileged assignment/publication/confirmation and adversarial requests used the app's authenticated API service from that phone. A separate laptop-side Admin login subsequently read persisted task, appointment, payroll and ERP results. Admin/HR payroll forms and manager ERP controls also passed Flutter widget tests.

Native GPS/camera used isolated executive 6 because the existing executive already had completed attendance today. No attendance was deleted or overwritten. The isolated account logged out and was deactivated after success. Test records are retained; payroll verification uses year 2099.

## Regression and security

- Full backend: **46 passed** (one existing SQLAlchemy Query.get deprecation warning).
- Full Flutter: **37 passed**.
- `flutter analyze`: **No issues found**.
- Four real-device integration cases passed across focused runs: task/appointment; payroll/ERP/security; GPS attendance; camera onboarding.
- Route inventory: `release-api-route-audit.csv` lists 54 API operations; 53 require JWT. Login is the sole public API operation. The full backend suite exercises missing and invalid JWTs across every protected operation.
- Executives cannot use administrative/manager-only operations or read foreign payroll/ERP records. Managers cannot manage payroll or use admin-only user/audit operations. HR cannot use ERP or field mutation endpoints.
- Every authenticated request rechecks account/employee activation and current database role. Logout revocations persist in the database. Sensitive API responses use Cache-Control: no-store.
- Shared authenticated client catalogue access remains intentional; client mutations, private photos and other owned records retain their respective role/ownership checks.

## Login investigation and test corrections

The first retry's phone API login failed before any UI action. Direct phone networking returned Connection refused because the configured `.108` address belonged to the phone, not the laptop. Local backend health was successful; phone health and API/UI login passed after the user-approved switch to `.107`.

Additional automation-only failures were corrected: asynchronous app/login startup waiting, scrolling before locating lazily built dashboard tiles, and scoping the salary assertion to the newly created record when several test records had equal amounts. Android canceled one install with INSTALL_FAILED_USER_RESTRICTED; the next accepted install succeeded. No application code was changed in this final verification pass. Changes were limited to verification harness/fixtures and relevant release documentation.

## Persisted acceptance evidence

- Task 6: started `2026-09-08T14:09:02.231022+00:00`, completed `2026-09-08T14:09:03.069660+00:00`, three status history entries and three activities.
- Appointment 5: `2026-09-09T14:09:00+00:00` (19:39 IST); edited notes persisted.
- Payroll 4: employee 4, published, net 12445.67.
- ERP order 2: employee 4, Confirmed.
- Attendance 3: check-in `2026-09-08T14:14:44.912488+00:00`; check-out `2026-09-08T14:14:45.624454+00:00`; both include GPS/accuracy. Precise coordinates omitted here.
- Client 4 and photo 3: successful onboarding and authenticated image retrieval.

## Release APK

Build command: `flutter build apk --release --dart-define=API_BASE_URL=http://192.168.0.107:5000/api`

Release build: **PASS**. Artifact: `C:/Users/Asus/Documents/ChatGPT/marketing_field_task_manager/mobile_app/build/app/outputs/flutter-apk/app-release.apk`

- Version: 1.0.0 (build 1); size: 55,153,003 bytes.
- SHA-256: `e626fd2308b2adddb31c1863a663add2f26641ef582dd3ff3604162114a76d77`.
- APK signature verification: PASS (v2, existing Android Debug certificate).
- ZIP alignment and 16 KiB native-library alignment check: PASS.
- Compiled arm64-v8a, armeabi-v7a and x86_64 libraries contain the approved `.107` API URL; demo passwords are absent from those application libraries.
- Manifest retains INTERNET, CAMERA, fine/coarse location permissions; release manifest does not set debuggable.
- Installed on device `22b01c1e`: Success. Cold launch: Status ok; app process running.
- Core workflow verification used the instrumented debug build; the final release artifact was separately verified, installed and launched.
The existing release signing configuration uses the Android debug certificate. This is an internal MVP release-mode APK, not a store-signing handoff. The release build uses `lib/main.dart`; private integration-test credential files are not build inputs.
