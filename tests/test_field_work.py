from datetime import datetime
import pytest
from conftest import auth, token
from extensions import db
from models import Activity, TaskUpdate, User

def setup_flow(client):
    manager = auth(token(client, "manager"))
    owner = auth(token(client, "exec1"))
    other = auth(token(client, "exec2"))
    employee = client.get("/api/auth/me", headers=owner).json["data"]["employee"]["id"]
    row = client.post("/api/tasks", headers=manager, json={"title": "Visit client", "assigned_employee_id": employee}).json["data"]
    return manager, owner, other, employee, row

def test_status_history_timestamps_and_admin_visibility(client, app):
    manager, owner, other, employee, row = setup_flow(client)
    path = f"/api/tasks/{row['id']}"
    assert row["status"] == "Pending"
    assert row["created_at"].endswith("+00:00")
    assert client.patch(path, headers=owner, json={"status": "Completed"}).status_code == 409
    assert client.patch(path, headers=other, json={"status": "In Progress"}).status_code == 403
    assert client.get(path + "/history", headers=other).status_code == 403
    assert client.post(path + "/updates", headers=owner, json={"status": "In Progress"}).status_code == 201
    # Replayed status is idempotent and does not append a second event.
    assert client.patch(path, headers=owner, json={"status": "In Progress"}).status_code == 200
    assert client.patch(path, headers=owner, json={"status": "Completed", "remarks": "Done"}).status_code == 200
    assert client.patch(path, headers=owner, json={"status": "Pending"}).status_code == 409
    detail = client.get(path, headers=manager).json["data"]
    assert [x["status"] for x in detail["history"]] == ["Pending", "In Progress", "Completed"]
    assert datetime.fromisoformat(detail["started_at"]) <= datetime.fromisoformat(detail["completed_at"])
    with app.app_context():
        assert TaskUpdate.query.filter_by(task_id=row["id"]).count() == 3
        assert Activity.query.filter_by(task_id=row["id"]).count() == 3
    activity = client.get(f"/api/activities/employees/{employee}", headers=manager).json["data"]
    assert activity[0]["type"] == "TASK_STATUS_CHANGE"
    assert activity[0]["employee_id"] == employee
    assert client.get(f"/api/activities/employees/{employee}", headers=owner).status_code == 403
    assert client.get("/api/tasks", headers=owner).status_code == 403
    assert client.get("/api/tasks/me", headers=other).json["data"] == []

@pytest.mark.parametrize("body", [
    [], {"title": "", "assigned_employee_id": 4},
    {"title": "X", "assigned_employee_id": 999},
    {"title": "X", "assigned_employee_id": True},
    {"title": "X", "assigned_employee_id": 1},
    {"title": "X", "assigned_employee_id": 4, "deadline": "bad"},
    {"title": "X", "assigned_employee_id": 4, "deadline": "2020-01-01"},
    {"title": "X", "assigned_employee_id": 4, "priority": "Anything"},
])
def test_task_input_validation(client, body):
    response = client.post("/api/tasks", headers=auth(token(client, "admin")), json=body)
    assert response.status_code == 422
    assert response.json["message"]

def test_status_validation_and_role_revocation(client, app):
    manager, owner, _, _, row = setup_flow(client)
    path = f"/api/tasks/{row['id']}"
    for payload in ({"status": "Bogus"}, {"status": []}, {"status": "In Progress", "created_at": "fake"}, []):
        assert client.patch(path, headers=owner, json=payload).status_code == 422
    assert client.get(path, headers=auth(token(client, "hr"))).status_code == 403
    with app.app_context():
        user = User.query.filter_by(username="exec1").one()
        user.active = False
        db.session.commit()
    assert client.patch(path, headers=owner, json={"status": "In Progress"}).status_code == 403
    assert len(client.get(path, headers=manager).json["data"]["history"]) == 1

def test_appointment_create_edit_ownership_upcoming_and_activity(client):
    owner, other = auth(token(client, "exec1")), auth(token(client, "exec2"))
    admin = auth(token(client, "admin"))
    client_row = client.post("/api/clients", headers=owner, json={"business_name": "Store", "contact_person": "A", "mobile": "9876543210", "address": "Road"}).json["data"]
    payload = {"client_id": client_row["id"], "appointment_at": "2099-09-10T10:00:00+05:30", "notes": "Bring samples"}
    response = client.post("/api/appointments", headers=owner, json=payload)
    assert response.status_code == 201
    row = response.json["data"]
    assert row["appointment_at"] == "2099-09-10T04:30:00+00:00"
    assert row["notes"] == "Bring samples"
    path = f"/api/appointments/{row['id']}"
    assert client.get(path, headers=other).status_code == 403
    assert client.patch(path, headers=other, json={"notes": "Attack"}).status_code == 403
    assert client.patch(path, headers=owner, json={"employee_id": 5}).status_code == 422
    changed = client.patch(path, headers=owner, json={"appointment_at": "2099-10-01T12:00:00Z", "notes": "Rescheduled"}).json["data"]
    assert changed["notes"] == "Rescheduled"
    assert changed["appointment_at"] == "2099-10-01T12:00:00+00:00"
    assert len(client.get("/api/appointments/me?upcoming=true", headers=owner).json["data"]) == 1
    assert client.get("/api/appointments/me", headers=other).json["data"] == []
    assert client.get("/api/appointments", headers=owner).status_code == 403
    assert client.get("/api/appointments", headers=admin).json["data"][0]["notes"] == "Rescheduled"
    assert client.patch(path, headers=owner, json={"status": "Cancelled"}).status_code == 200
    assert client.get("/api/appointments/me?upcoming=true", headers=owner).json["data"] == []
    events = client.get("/api/activities/me", headers=owner).json["data"]
    assert any(x["type"] == "APPOINTMENT_CREATED" for x in events)
    for bad in ([], {}, dict(payload, appointment_at="bad"), dict(payload, client_id=999), dict(payload, notes=42)):
        assert client.post("/api/appointments", headers=owner, json=bad).status_code == 422
    assert client.post("/api/appointments", headers=owner, json=dict(payload, employee_id=5)).status_code == 403
    assert client.post("/api/appointments", headers=auth(token(client, "hr")), json=payload).status_code == 403

def test_admin_web_field_page_and_authentication(client):
    assert client.get("/admin/field-work").status_code == 302
    client.post("/admin/login", data={"username": "manager", "password": "Demo@123"})
    page = client.get("/admin/field-work")
    assert page.status_code == 200
    assert b"Assign task" in page.data
    for path in ("/api/tasks", "/api/tasks/executives", "/api/appointments", "/api/appointments/me", "/api/activities/employees/4"):
        assert client.get(path).status_code == 401
