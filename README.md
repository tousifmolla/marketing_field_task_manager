# Marketing Field Task Management System

A free, local-first MVP for field marketing operations. It combines a Flutter executive app, Flask REST API, secure role-based access, SQLite, local photo storage and a responsive manager dashboard.

## Features

- JWT login with Admin, Manager, HR/Accounts and Marketing Executive roles
- GPS-backed check-in/out, duplicate prevention and attendance history
- Explicit work-operation location capture; no covert 24/7 tracking
- Client onboarding, visits, location and photo metadata
- Task assignment, status updates, proof architecture and audit trail
- Appointments and automatic activity timeline
- Own published payroll for employees; Admin/HR payroll creation, editing and publication with server-calculated net salary
- ERP drafts owned by executives, server-priced order items and Admin/Manager confirmation
- In-app alerts, unread state and CSV attendance export
- Responsive Bootstrap administration dashboard

## Architecture and folders

```text
backend/     Flask app factory, Blueprints, models, services, Jinja dashboard
mobile_app/  Flutter client, provider state, API/domain services and screens
database/    Reference schema and seed guidance
tests/       Authentication, RBAC and critical workflow integration tests
docs/        API, database, architecture and user manual
scripts/     Windows launcher
```

## Backend setup — Windows PowerShell

```powershell
cd C:\Users\Asus\Documents\ChatGPT\marketing_field_task_manager\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python seed.py
python app.py
```

API: `http://127.0.0.1:5000/api`  
Admin dashboard: `http://127.0.0.1:5000/admin/login`

The development server listens on `0.0.0.0` by default for phone testing. Windows Firewall may ask permission for private networks.

## Demo credentials

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `Admin@123` |
| Manager | `manager` | `Manager@123` |
| HR/Accounts | `hr` | `Hr@12345` |
| Marketing Executive | `executive` | `Executive@123` |

These are intentionally obvious demo credentials. Change them before real use. Signing secrets come from explicit strong environment values or the private generated `backend/instance/security.json`; keep that file private and backed up.

## Flutter setup

Install the stable Flutter SDK and Android Studio, then complete native scaffolding if this folder was transferred without generated platform files:

```powershell
cd C:\Users\Asus\Documents\ChatGPT\marketing_field_task_manager\mobile_app
flutter create --platforms=android .
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:5000/api
```

For an Android emulator, `10.0.2.2` reaches the Windows host. For a physical phone, use the laptop's LAN IP.

## Physical Android phone

1. Connect the phone and laptop to the same private Wi-Fi.
2. Run `ipconfig` and find the laptop's Wi-Fi **IPv4 Address**.
3. Start Flask and allow Python through Windows Firewall on private networks.
4. Enable USB debugging, connect the phone, and confirm it appears in `flutter devices`.
5. Run:

```powershell
flutter run --dart-define=API_BASE_URL=http://YOUR_LAPTOP_IP:5000/api
```

Do not hard-code the IP. It can change when the laptop reconnects.

## Android permissions

- Internet: communicates with the Flask API.
- Fine/coarse location: captures attendance, visits and explicit field locations.
- Camera: captures client and proof photos.

Permissions are requested at runtime only when the related action is used.

## Tests

```powershell
cd backend
.\venv\Scripts\python.exe -m pytest ..\tests -q
.\venv\Scripts\python.exe -m compileall -q . ..\tests
```

When Flutter is installed:

```powershell
flutter analyze
flutter test
```

## Known MVP limitations

- Local SQLite and uploads suit one demo server, not a distributed deployment.
- Logout revokes the JWT in the database and clears the device session. Offline logout clears the local session but cannot revoke the server token until the server is reachable.
- In-app alerts are implemented; FCM push delivery is not configured.
- The mobile UI includes task transitions, appointment editing, payroll management and ERP draft/confirmation forms. Offline queueing and map marker screens remain future work.
- Payroll calculation is deliberately generic and is not statutory payroll software.
- PDF payslip rendering, inventory, purchasing, invoicing and accounting are future extensions.

## Production recommendations

Use PostgreSQL with Alembic migrations, HTTPS behind a production WSGI server, private object storage, malware/image-content validation, rate limiting, refresh-token rotation, centralized logs/backups, FCM, strict CORS, privacy retention rules and automated deployment. Validate payroll and employee monitoring rules with local legal/HR advisers.
