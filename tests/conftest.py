import sys
from pathlib import Path
import pytest

BACKEND=Path(__file__).resolve().parents[1]/"backend"; sys.path.insert(0,str(BACKEND))
from app import create_app
from config import TestConfig
from extensions import db
from models import Client, Employee, Payroll, Product, Role, Task, User

@pytest.fixture()
def app():
    app=create_app(TestConfig)
    with app.app_context():
        db.create_all(); roles={x:Role(name=x) for x in ("ADMIN","MANAGER","HR_ACCOUNTS","MARKETING_EXECUTIVE")};db.session.add_all(roles.values());db.session.flush()
        for username,role,code in (("admin","ADMIN","A1"),("manager","MANAGER","M1"),("hr","HR_ACCOUNTS","H1"),("exec1","MARKETING_EXECUTIVE","E1"),("exec2","MARKETING_EXECUTIVE","E2")):
            u=User(username=username,role=roles[role]);u.set_password("Demo@123");db.session.add(u);db.session.flush();db.session.add(Employee(user_id=u.id,employee_code=code,name=username.title(),designation=role,basic_salary=30000))
        db.session.commit();yield app;db.session.remove();db.drop_all()
@pytest.fixture()
def client(app):
    return app.test_client()
def token(client,username,password="Demo@123"):
    response=client.post("/api/auth/login",json={"username":username,"password":password});return response.get_json()["data"]["access_token"]
def auth(value):return {"Authorization":f"Bearer {value}"}
