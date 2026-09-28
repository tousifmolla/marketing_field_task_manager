import io
from decimal import Decimal
from flask_jwt_extended import create_access_token
from conftest import auth, token
from extensions import db
from models import User, Employee, Payroll, Product, Client, Order, Notification, Task, Photo, RevokedToken
from test_client_onboarding import camera_photo

def credentials(client):
    return {name: auth(token(client, name)) for name in ("admin", "manager", "hr", "exec1", "exec2")}

def test_every_api_route_rejects_missing_and_invalid_jwt(client, app):
    import re
    checked = []
    for rule in app.url_map.iter_rules():
        if not rule.rule.startswith("/api/") or rule.rule == "/api/auth/login":
            continue
        path = re.sub(r"<[^>]+>", "999999", rule.rule)
        for method in rule.methods - {"HEAD", "OPTIONS"}:
            response = client.open(path, method=method, json={})
            assert response.status_code == 401, (method, path, response.status_code)
            forged = client.open(path, method=method, json={}, headers=auth("not-a-valid-jwt"))
            assert forged.status_code == 401, (method, path)
            checked.append((method, path))
    assert len(checked) >= 40

def test_role_matrix_rejects_privileged_routes(client):
    users = credentials(client)
    executive_denied = [
        ("GET", "/api/admin/dashboard"), ("POST", "/api/admin/users"),
        ("GET", "/api/admin/audit-logs"), ("GET", "/api/admin/reports/attendance.csv"),
        ("GET", "/api/attendance"), ("GET", "/api/location/latest"),
        ("GET", "/api/tasks"), ("POST", "/api/tasks"), ("GET", "/api/tasks/executives"),
        ("GET", "/api/appointments"), ("GET", "/api/activities/employees/4"),
        ("GET", "/api/payroll"), ("GET", "/api/payroll/employees"), ("POST", "/api/payroll"),
        ("PATCH", "/api/payroll/999999"), ("PATCH", "/api/erp/orders/999999"),
    ]
    for method, path in executive_denied:
        assert client.open(path, method=method, headers=users["exec1"], json={}).status_code == 403, path
    for method, path in [("GET","/api/payroll"), ("GET","/api/payroll/employees"), ("POST","/api/payroll"), ("PATCH","/api/payroll/999999"), ("GET","/api/admin/audit-logs"), ("POST","/api/admin/users")]:
        assert client.open(path, method=method, headers=users["manager"], json={}).status_code == 403, path
    for method, path in [("GET","/api/erp/products"), ("GET","/api/erp/orders"), ("POST","/api/erp/orders"), ("PATCH","/api/erp/orders/1"), ("POST","/api/tasks"), ("GET","/api/location/latest"), ("POST","/api/clients"), ("POST","/api/clients/onboard"), ("POST","/api/photos")]:
        assert client.open(path, method=method, headers=users["hr"], json={}).status_code == 403, path
    for name in ("admin", "manager", "hr"):
        with client.session_transaction() as session:
            session["user_id"] = {"admin":1, "manager":2, "hr":3}[name]
        response = client.get("/admin/field-work")
        assert response.status_code == (302 if name == "hr" else 200)

def test_payroll_ownership_drafts_upsert_updates_and_audit(client):
    users = credentials(client)
    p = {"employee_id":4, "year":2099, "month":1, "basic_salary":"30000.10",
         "ta_da":"100.25", "deductions":"50.05", "working_days":26, "present_days":24, "leave_days":2}
    response = client.post("/api/payroll", headers=users["hr"], json=p)
    assert response.status_code == 201
    row = response.json["data"]
    assert row["net_salary"] == 30050.30
    assert client.get("/api/payroll/me", headers=users["exec1"]).json["data"] == []
    assert client.get(f"/api/payroll/{row['id']}", headers=users["exec1"]).status_code == 403
    published = client.patch(f"/api/payroll/{row['id']}", headers=users["admin"], json={"published":True, "overtime":100})
    assert published.status_code == 200 and published.json["data"]["net_salary"] == 30150.30
    assert len(client.get("/api/payroll/me?employee_id=5", headers=users["exec1"]).json["data"]) == 1
    assert client.get("/api/payroll/me", headers=users["exec2"]).json["data"] == []
    assert client.get(f"/api/payroll/{row['id']}", headers=users["exec2"]).status_code == 403
    assert client.get(f"/api/payroll/{row['id']}", headers=users["manager"]).status_code == 403
    assert client.get("/api/payroll", headers=users["hr"]).json["data"][0]["employee_id"] == 4
    assert client.post("/api/payroll", headers=users["hr"], json=dict(p, published=True)).status_code == 200
    assert Payroll.query.count() == 1
    assert Notification.query.filter_by(notification_type="payroll").count() == 1
    assert client.patch(f"/api/payroll/{row['id']}", headers=users["hr"], json={"employee_id":5}).status_code == 422
    assert client.get("/api/admin/audit-logs", headers=users["admin"]).json["data"][0]["action"] == "PAYROLL_UPDATE"
    # Own published payroll is also available to managers; management remains forbidden.
    own = client.post("/api/payroll", headers=users["hr"], json=dict(p, employee_id=2, published=True)).json["data"]
    assert client.get("/api/payroll/me", headers=users["manager"]).json["data"][0]["id"] == own["id"]

def test_payroll_invalid_values_are_atomic(client):
    headers = auth(token(client, "hr"))
    valid = {"employee_id":4, "year":2099, "month":1, "basic_salary":1000}
    bad = [[], {}, dict(valid, month=13), dict(valid, year=True), dict(valid, employee_id=999),
           dict(valid, basic_salary="NaN"), dict(valid, basic_salary="Infinity"), dict(valid, basic_salary=-1),
           dict(valid, published="false"), dict(valid, present_days=32),
           dict(valid, working_days=20, present_days=21), dict(valid, deductions=2000),
           dict(valid, net_salary=1), dict(valid, basic_salary=True)]
    for p in bad:
        response = client.post("/api/payroll", headers=headers, json=p)
        assert response.status_code == 422, p
        assert Payroll.query.count() == 0

def commerce_data():
    c = Client(client_code="SEC-CLI", business_name="Security Store", contact_person="Test", mobile="9876543210", address="Road", created_by=4)
    p = Product(product_code="SEC-PRD", product_name="Test package", price=Decimal("123.45"), status="Active")
    db.session.add_all([c,p]); db.session.commit()
    return c,p

def test_erp_role_ownership_server_prices_and_transitions(client):
    users = credentials(client)
    c,p = commerce_data()
    payload = {"client_id":c.id, "items":[{"product_id":p.id, "quantity":3}]}
    made = client.post("/api/erp/orders", headers=users["exec1"], json=payload)
    assert made.status_code == 201
    row = made.json["data"]
    assert row["amount"] == 370.35 and row["status"] == "Draft" and row["executive_id"] == 4
    path = f"/api/erp/orders/{row['id']}"
    assert client.get(path, headers=users["exec2"]).status_code == 403
    assert client.get("/api/erp/orders?executive_id=4", headers=users["exec2"]).json["data"] == []
    assert client.get(path, headers=users["manager"]).status_code == 200
    assert client.patch(path, headers=users["exec1"], json={"status":"Confirmed"}).status_code == 403
    assert client.patch(path, headers=users["manager"], json={"status":"Confirmed"}).status_code == 200
    assert client.patch(path, headers=users["admin"], json={"status":"Cancelled"}).status_code == 409
    assert client.post("/api/erp/orders", headers=users["exec1"], json=dict(payload, executive_id=5)).status_code == 403
    assert client.post("/api/erp/orders", headers=users["manager"], json=dict(payload, executive_id=5)).status_code == 201
    assert client.post("/api/erp/orders", headers=users["hr"], json=payload).status_code == 403
    assert Order.query.count() == 2

def test_erp_bad_items_prices_status_and_ids_are_rejected(client):
    h = auth(token(client,"exec1"))
    c,p = commerce_data()
    good = {"client_id":c.id, "items":[{"product_id":p.id, "quantity":1}]}
    for bad in ([], {}, dict(good, amount=0), dict(good, status="Confirmed"), dict(good, client_id=999),
                dict(good, items=[{"product_id":p.id,"quantity":1,"unit_price":0}]),
                dict(good, items=[{"product_id":p.id,"quantity":True}]),
                dict(good, items=[{"product_id":p.id,"quantity":"2"}]),
                dict(good, items=[{"product_id":p.id,"quantity":-1}]),
                dict(good, items=[{"product_id":p.id,"quantity":1}]*2)):
        assert client.post("/api/erp/orders", headers=h, json=bad).status_code == 422, bad
        assert Order.query.count() == 0
    p.status = "Inactive"; db.session.commit()
    assert client.post("/api/erp/orders", headers=h, json=good).status_code == 422

def test_revoked_disabled_deleted_and_stale_role_tokens(client, app):
    users = credentials(client)
    assert client.post("/api/auth/logout", headers=users["exec2"]).status_code == 200
    assert RevokedToken.query.count() == 1
    assert client.get("/api/auth/me", headers=users["exec2"]).status_code == 401
    # JWT role claims cannot retain privileges after the database role changes.
    admin = db.session.get(User,1)
    admin.role_id = db.session.get(User,4).role_id
    db.session.commit()
    assert client.get("/api/payroll", headers=users["admin"]).status_code == 403
    user = db.session.get(User,4); user.active=False; db.session.commit()
    for path in ("/api/auth/me", "/api/clients", "/api/attendance/me", "/api/payroll/me", "/api/notifications", "/api/erp/products"):
        assert client.get(path, headers=users["exec1"]).status_code == 403, path
    with app.app_context():
        for identity in ("999999", "not-an-integer"):
            missing = create_access_token(identity=identity)
            assert client.get("/api/auth/me",headers=auth(missing)).status_code == 403

def test_cross_owner_client_photo_notification_and_location(client):
    users = credentials(client)
    c,p = commerce_data()
    assert client.put(f"/api/clients/{c.id}", headers=users["exec2"], json={"business_name":"Tampered"}).status_code == 403
    assert db.session.get(Client,c.id).business_name == "Security Store"
    task = Task(task_code="SEC-TASK",title="Owned",assigned_employee_id=4,assigned_by=1)
    db.session.add(task)
    note = Notification(user_id=4,title="Private",message="Only owner")
    db.session.add(note); db.session.commit()
    assert client.patch(f"/api/notifications/{note.id}/read",headers=users["exec2"]).status_code == 404
    assert not db.session.get(Notification,note.id).is_read
    response = client.post("/api/photos", headers=users["exec2"], data={"task_id":str(task.id),"photo":(camera_photo(),"camera.jpg")})
    assert response.status_code == 403 and Photo.query.count() == 0
    assert client.get("/api/location/me?employee_id=4",headers=users["exec2"]).json["data"] == []

def test_private_api_responses_and_disabled_web_accounts(client):
    headers = auth(token(client, "manager"))
    assert client.get("/api/auth/me", headers=headers).headers["Cache-Control"] == "no-store"
    with client.session_transaction() as session:
        session["user_id"] = 2
    employee = db.session.get(Employee, 2)
    employee.active = False
    db.session.commit()
    assert client.get("/admin").status_code == 302
    assert client.get("/api/auth/me", headers=headers).status_code == 403
    assert client.post("/api/auth/login", json={"username":"manager","password":"Demo@123"}).status_code == 401
