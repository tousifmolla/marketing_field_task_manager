import io
from conftest import auth, token

def test_login_and_me(client):
    response=client.post("/api/auth/login",json={"username":"exec1","password":"Demo@123"});assert response.status_code==200
    t=response.get_json()["data"]["access_token"];assert client.get("/api/auth/me",headers=auth(t)).get_json()["data"]["username"]=="exec1"
def test_invalid_login_and_unauthorized(client):
    assert client.post("/api/auth/login",json={"username":"exec1","password":"wrong"}).status_code==401
    assert client.get("/api/tasks/me").status_code==401
def test_rbac_blocks_executive_admin(client):
    assert client.get("/api/admin/audit-logs",headers=auth(token(client,"exec1"))).status_code==403
def test_attendance_full_flow_and_duplicate(client):
    h=auth(token(client,"exec1"));payload={"latitude":22.57,"longitude":88.36,"accuracy":8}
    assert client.post("/api/attendance/check-in",json=payload,headers=h).status_code==201
    assert client.post("/api/attendance/check-in",json=payload,headers=h).status_code==409
    assert client.post("/api/attendance/check-out",json=payload,headers=h).status_code==200
    assert len(client.get("/api/attendance/me",headers=h).get_json()["data"])==1
def test_checkout_without_checkin(client):assert client.post("/api/attendance/check-out",json={},headers=auth(token(client,"exec1"))).status_code==409
def test_client_validation_and_creation(client):
    h=auth(token(client,"exec1"));assert client.post("/api/clients",json={"business_name":"X"},headers=h).status_code==422
    p={"business_name":"Demo Store","contact_person":"Asha","mobile":"9876543210","address":"Kolkata","pin_code":"700001","latitude":22.5,"longitude":88.3};assert client.post("/api/clients",json=p,headers=h).status_code==201
def test_task_assignment_and_isolation(client):
    manager=auth(token(client,"manager"));e1=client.get("/api/auth/me",headers=auth(token(client,"exec1"))).get_json()["data"]["employee"]["id"]
    response=client.post("/api/tasks",json={"title":"Field visit","assigned_employee_id":e1,"priority":"High"},headers=manager);assert response.status_code==201;task_id=response.get_json()["data"]["id"]
    assert client.get(f"/api/tasks/{task_id}",headers=auth(token(client,"exec2"))).status_code==403
    assert client.patch(f"/api/tasks/{task_id}",json={"status":"In Progress"},headers=auth(token(client,"exec1"))).status_code==200
def test_appointment_and_photo_validation(client):
    h=auth(token(client,"exec1"));c=client.post("/api/clients",json={"business_name":"Shop","contact_person":"Asha","mobile":"9876543210","address":"Road"},headers=h).get_json()["data"]
    assert client.post("/api/appointments",json={"client_id":c["id"],"appointment_at":"2026-09-10T10:00:00","purpose":"Meet"},headers=h).status_code==201
    bad={"photo":(io.BytesIO(b"not image"),"test.exe")};assert client.post("/api/photos",data=bad,headers=h,content_type="multipart/form-data").status_code==415
def test_payroll_authorization(client):
    assert client.post("/api/payroll",json={},headers=auth(token(client,"manager"))).status_code==403
    assert client.get("/api/payroll/me",headers=auth(token(client,"exec1"))).status_code==200
