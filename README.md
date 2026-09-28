# Marketing Field Task Management System

**A full-stack field workforce management application built with Python Flask, Flutter and SQLite.**

A local-first application designed to digitize field marketing operations, including employee attendance, GPS-based field activities, customer onboarding, task management, payroll, ERP workflows and administrative monitoring.

The system combines a Flutter Android application, Flask REST API, role-based authentication and a responsive web administration dashboard.

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| Mobile Application | Flutter, Dart |
| Database | SQLite |
| API | REST API |
| Authentication | JWT, Role-Based Access Control |
| Web Dashboard | HTML, CSS, Bootstrap, Jinja2 |
| ORM | SQLAlchemy |
| Testing | Pytest, Flutter Test |
| Version Control | Git, GitHub |

## Key Features

### Authentication and Security
- JWT-based authentication.
- Four user roles: Admin, Manager, HR/Accounts and Marketing Executive.
- Role-based access restrictions.
- Audit trails for critical operations.
- Server-side validation.

### Attendance and GPS
- GPS-backed employee check-in and check-out.
- Duplicate attendance prevention.
- Attendance history.
- Explicit field-operation location capture.
- No covert or continuous 24/7 location tracking.

### Customer and Field Management
- Customer onboarding.
- Client visit records.
- GPS location and photo metadata.
- Field activity timeline.
- Task assignment and status tracking.
- Appointment management.

### Payroll and ERP
- Employee access to their own published payroll.
- Admin/HR payroll management.
- Server-calculated net salary.
- ERP order drafts.
- Server-priced order items.
- Admin/Manager order confirmation.

### Administration
- Responsive Bootstrap dashboard.
- Employee and task management.
- Attendance monitoring.
- CSV attendance export.
- In-app notifications and unread status.

## Application Screenshots

### Login Screen

![Login Screen](screenshots/login.png)

### Admin Dashboard

![Admin Dashboard](screenshots/admin-dashboard.png)

### Employee Attendance

![Attendance](screenshots/attendance.png)

### Flutter Mobile Application

![Mobile Application](screenshots/mobile-app.png)

*Screenshots should be captured from the running application using demonstration data.*

## System Architecture

```text
          Flutter Android Application
                     |
                     |
                  REST API
                     |
              Flask Application
                     |
          JWT Authentication / RBAC
                     |
          Business Logic / Services
                     |
                 SQLAlchemy
                     |
               SQLite Database

             Flask Application
                     |
              Jinja2 Templates
                     |
          Bootstrap Admin Dashboard
```

## Project Structure

```text
marketing_field_task_manager/
|
|-- backend/
|   |-- models/
|   |-- routes/
|   |-- services/
|   |-- middleware/
|   |-- templates/
|   |-- static/
|   |-- app.py
|   |-- seed.py
|   |-- requirements.txt
|
|-- mobile_app/
|   |-- lib/
|   |-- pubspec.yaml
|
|-- database/
|-- deployment/
|-- docs/
|-- scripts/
|-- tests/
|-- screenshots/
|
|-- README.md
|-- .gitignore
```

## Installation Instructions

### Prerequisites

- Python 3
- Flutter SDK
- Android Studio
- Git
- Windows 10/11 or a compatible development environment

### 1. Clone the repository

```bash
git clone https://github.com/tousifmolla/marketing_field_task_manager.git
cd marketing_field_task_manager
```

### 2. Backend setup (Windows PowerShell)

```powershell
cd backend

python -m venv venv

.\venv\Scripts\Activate.ps1

python -m pip install -r requirements.txt

Copy-Item .env.example .env

python seed.py

python app.py
```

Backend API:

http://127.0.0.1:5000/api

Admin dashboard:

http://127.0.0.1:5000/admin/login

The development server listens on `0.0.0.0` by default to support testing with physical Android devices.

### 3. Demo Credentials

| Role | Username | Password |
|---|---|---|
| Admin | admin | Admin@123 |
| Manager | manager | Manager@123 |
| HR/Accounts | hr | Hr@12345 |
| Marketing Executive | executive | Executive@123 |

**Security notice:** These credentials are intended exclusively for local demonstration. Change them before using the application with real data or exposing it to a network.

Signing secrets must remain private. Do not commit `.env` or `backend/instance/security.json`.

### 4. Flutter Application Setup

```powershell
cd mobile_app

flutter create --platforms=android .

flutter pub get

flutter run --dart-define=API_BASE_URL=http://10.0.2.2:5000/api
```

For an Android emulator, `10.0.2.2` connects to the Windows host.

For a physical Android phone, use the laptop's local IPv4 address instead.

### 5. Physical Android Device

1. Connect your phone and laptop to the same private Wi-Fi.
2. Run `ipconfig` to find your laptop's IPv4 address.
3. Start the Flask backend.
4. Allow Python through Windows Firewall on private networks.
5. Enable USB debugging and connect your phone.
6. Verify connectivity using `flutter devices`.

Run:

```powershell
flutter run --dart-define=API_BASE_URL=http://YOUR_LAPTOP_IP:5000/api
```

## Android Permissions

The application requests the following permissions when needed:

| Permission | Purpose |
|---|---|
| Internet | Backend API communication |
| Fine/Coarse Location | Attendance and field activities |
| Camera | Client and proof photo capture |

## Testing

Backend:

```powershell
cd backend

.\venv\Scripts\python.exe -m pytest ..\tests -q

.\venv\Scripts\python.exe -m compileall -q . ..\tests
```

Flutter:

```powershell
cd mobile_app

flutter analyze

flutter test
```

## Documentation

Additional technical documentation is available in the `docs/` directory:

- API documentation
- Database design
- System architecture
- User manual
- Deployment instructions

## Known MVP Limitations

- SQLite and local photo storage are intended for a single-server demonstration.
- Offline logout clears the local session but cannot immediately revoke the server token.
- FCM push notifications are not configured.
- Offline queueing and map marker screens remain future improvements.
- Payroll calculations are generic and are not statutory payroll software.
- PDF payslips, inventory, purchasing, invoicing and accounting remain future extensions.

## Future Enhancements

- PostgreSQL and Alembic migrations.
- Production deployment with HTTPS.
- Firebase Cloud Messaging.
- Offline mobile synchronization.
- Advanced reporting and analytics.
- Secure cloud photo storage.
- Automated deployment and monitoring.

## Developer

**Tousif Ali Molla**

B.Tech – Information Technology

GitHub: https://github.com/tousifmolla

Project Repository: https://github.com/tousifmolla/marketing_field_task_manager

---

*Developed as a full-stack software development portfolio project demonstrating Python backend development, REST APIs, Flutter integration, authentication, database management and business workflow automation.*