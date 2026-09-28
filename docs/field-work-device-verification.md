# Tasks, appointments and activity — device verification

Verified on 8 September 2026 using device `22b01c1e` (24066PC95I) against `http://192.168.0.108:5000/api`.

## Result

The complete real-device acceptance test passed twice. The final run explicitly verified the appointment client and local appointment time rendered inside the dashboard's Upcoming appointments card.

Final acceptance records remain available for review:

- Task **4**, `TSK-1bcf094c15ae4d1693973844`, titled `Device task verification 1788845098357`.
- Assigned by Admin (user 1) to executive Arjun Sen (employee 4).
- Pending: 8 September 2026, **10:54:58 AM IST**.
- In Progress: **10:55:01 AM IST**, changed through the phone UI by executive user 4.
- Completed: **10:55:02 AM IST**, changed through the phone UI by executive user 4.
- The task has three persisted history events and three corresponding executive activity entries. The admin API and the manager web interface both showed the completed status and history.
- Appointment **3**, `APT-dd85ba2eaa124b7aaea519b9`, created and edited through the phone UI.
- Client: `Device Camera Verification 1788683312670`.
- Appointment time: **9 September 2026, 10:55 AM IST**.
- Saved notes: `Device appointment edited 1788845098357`.
- Appointment creation/update activity and edited notes were visible in the manager interface.

Manager review page: [Tasks, appointments and activity](http://192.168.0.108:5000/admin/field-work).

## Login investigation

The original failed test only established that DashboardScreen was absent; its output did not retain a server error, so its exact transient cause cannot be proven retrospectively.

A subsequent retry failed before starting the app: Android reported `INSTALL_FAILED_USER_RESTRICTED: Install canceled by user`. When verification resumed on 8 September, the USB-connected phone's Wi-Fi interface initially had no connection. The user restored Wi-Fi, and the device obtained 192.168.0.109.

Executive login succeeded directly through the specified API, returning the Marketing Executive role, employee 4, and a JWT. After connectivity and installation were available, the real phone's existing login form succeeded in both complete acceptance runs. No login implementation changes were required.

The test now retains the login provider's error on failure and emits a specific successful-login verification marker.

## Checks

| Check | Result |
| --- | --- |
| Full backend suite: `backend/venv/Scripts/python.exe -m pytest tests -q` | 37 passed |
| Full Flutter suite: `flutter test` | 28 passed |
| `flutter analyze` | No issues found |
| Final device acceptance test | 1 passed, exit 0 |

Backend checks cover task transitions, timestamp/history persistence, idempotent status replay, JWT/RBAC, ownership, inactive accounts, appointment validation, appointment updates, upcoming filtering, and manager access. Existing Login, Attendance/GPS and Client/Camera regression tests passed.

Final device output:

```text
LOGIN_DEVICE_VERIFIED executive UI login succeeded
TASK_DEVICE_VERIFIED id=4 status=Completed history=3
APPOINTMENT_DEVICE_VERIFIED id=3 notes=edited upcoming=true
00:21 +1: All tests passed!
```

One existing Flask-SQLAlchemy legacy Query.get warning remains in the client onboarding test. The backend suite passed.

## Scope and rerun

This verification follow-up changed only `mobile_app/integration_test/field_work_flow_test.dart` and this report. It retained all existing application modules.

Set the existing demo passwords in the named environment variables before rerunning:

```powershell
flutter test integration_test/field_work_flow_test.dart -d 22b01c1e --dart-define=API_BASE_URL=http://192.168.0.108:5000/api --dart-define=DEMO_PASSWORD="$env:FIELD_EXECUTIVE_PASSWORD" --dart-define=ADMIN_PASSWORD="$env:FIELD_ADMIN_PASSWORD"
```

Keep the phone on the laptop's Wi-Fi, unlocked, and accept Android's installation prompt. Each acceptance run creates clearly labeled task and appointment records.
