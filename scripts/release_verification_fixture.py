"""Create an isolated, disabled test executive and foreign records for phone RBAC checks."""
import json
import secrets
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "backend"))
from app import app
from extensions import db
from models import User, Employee, Role, Payroll, Order, OrderItem, Product, Client
from flask_jwt_extended import create_access_token

with app.app_context():
    marker = uuid4().hex[:12]
    password = secrets.token_urlsafe(24)
    user = User(username=f"release_probe_{marker}", role=Role.query.filter_by(name="MARKETING_EXECUTIVE").one())
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    employee = Employee(employee_code=f"PROBE-{marker}", name="Release security probe", user_id=user.id, designation="Verification only")
    db.session.add(employee)
    db.session.flush()
    payroll = Payroll(employee_id=employee.id,year=2099,month=12,basic_salary=Decimal("77"),net_salary=Decimal("77"),published=True)
    product = Product.query.filter_by(status="Active").first()
    client = Client.query.first()
    assert product and client
    order = Order(order_number=f"ORD-PROBE-{marker}",client_id=client.id,executive_id=employee.id,order_date=date.today(),amount=product.price,status="Draft")
    order.items.append(OrderItem(product_id=product.id,quantity=1,unit_price=product.price))
    db.session.add_all([payroll,order])
    db.session.flush()
    # Issue a valid session first, then deactivate before committing the fixture.
    previous_token = create_access_token(identity=str(user.id))
    user.active = False
    db.session.commit()
    values = {
        "API_BASE_URL":"http://192.168.0.108:5000/api",
        "DEMO_PASSWORD":"Executive@123","ADMIN_PASSWORD":"Admin@123",
        "HR_PASSWORD":"Hr@12345","MANAGER_PASSWORD":"Manager@123",
        "PROBE_USERNAME":user.username,"PROBE_PASSWORD":password,"INACTIVE_TOKEN":previous_token,
        "FOREIGN_PAYROLL_ID":str(payroll.id),"FOREIGN_ORDER_ID":str(order.id)
    }
    target = root / "backend" / "instance" / "release-smoke-secrets.json"
    target.write_text(json.dumps(values),encoding="utf-8")
    print(f"Disabled test actor {user.id}; foreign payroll {payroll.id}; foreign order {order.id}. No existing account changed.")
