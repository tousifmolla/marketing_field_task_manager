# API

All API responses use `{ "success": boolean, "message": string, "data": ... }`. Send JWTs as `Authorization: Bearer <token>`.

## Main endpoints

- `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/logout`
- `POST /api/attendance/check-in`, `POST /api/attendance/check-out`, `GET /api/attendance/me`
- `POST /api/location/update`, `GET /api/location/me`, `GET /api/location/latest`
- `POST|GET /api/clients`, `GET|PUT /api/clients/<id>`
- `POST /api/client-visits`, `GET /api/client-visits/me`
- `GET /api/tasks/me`, `GET|PATCH /api/tasks/<id>`, `POST /api/tasks`, `POST /api/tasks/<id>/updates`
- `GET /api/appointments/me`, `POST /api/appointments`, `PATCH /api/appointments/<id>`
- `GET /api/activities/me`, `POST /api/photos`, `GET /api/payroll/me`
- `GET /api/notifications`, `PATCH /api/notifications/<id>/read`
- `GET /api/erp/products`, `GET|POST /api/erp/orders`
- `GET /api/admin/dashboard`, `POST /api/admin/users`, `GET /api/admin/audit-logs`
- `GET /api/admin/reports/attendance.csv`

Admin APIs enforce role membership. Executive-owned resources are resolved from JWT identity.
