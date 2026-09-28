import os
from datetime import date, datetime, timedelta
from app import create_app
from extensions import db
from models import Appointment, Client, Employee, Notification, Product, Role, Task, User
app=create_app()
def seed():
    db.drop_all(); db.create_all(); roles={name:Role(name=name) for name in ("ADMIN","MANAGER","HR_ACCOUNTS","MARKETING_EXECUTIVE")}; db.session.add_all(roles.values()); db.session.flush()
    specs=[("admin","Admin@123","ADMIN","EMP-001","System Administrator","Administrator"),("manager","Manager@123","MANAGER","EMP-002","Maya Kapoor","Marketing Manager"),("hr","Hr@12345","HR_ACCOUNTS","EMP-003","Rohan Das","HR & Accounts"),("executive","Executive@123","MARKETING_EXECUTIVE","EMP-004","Arjun Sen","Marketing Executive")]; users={}
    for username,password,role,code,name,title in specs:
        u=User(username=username,role=roles[role]);u.set_password(password);db.session.add(u);db.session.flush();e=Employee(employee_code=code,user_id=u.id,name=name,email=f"{username}@demo.local",phone="9876543210",designation=title,basic_salary=30000 if username=="executive" else 50000);db.session.add(e);users[username]=(u,e)
    db.session.flush(); users["executive"][1].manager_id=users["manager"][1].id
    client=Client(client_code="CLI-DEMO-001",business_name="Eastern Retail House",contact_person="Priya Ghosh",mobile="9876501234",address="22 Park Street",city="Kolkata",district="Kolkata",state="West Bengal",pin_code="700016",latitude=22.552,longitude=88.352,business_type="Retail",interested_product="Premium Package",expected_order_value=75000,created_by=users["executive"][0].id);db.session.add(client);db.session.flush()
    db.session.add_all([Product(product_code="PRD-001",product_name="Starter Package",category="Services",price=15000),Product(product_code="PRD-002",product_name="Premium Package",category="Services",price=35000)])
    task=Task(task_code="TSK-DEMO-001",title="Visit Eastern Retail House",description="Present the premium package and collect requirements",assigned_employee_id=users["executive"][1].id,assigned_by=users["manager"][0].id,client_id=client.id,location=client.address,priority="High",start_date=date.today(),deadline=date.today()+timedelta(days=2),status="Not Started");db.session.add(task)
    db.session.add(Appointment(appointment_code="APT-DEMO-001",client_id=client.id,employee_id=users["executive"][1].id,appointment_at=datetime.now()+timedelta(hours=2),purpose="Product presentation",address=client.address))
    db.session.add(Notification(user_id=users["executive"][0].id,title="New task assigned",message=task.title,notification_type="task"));db.session.commit()
if __name__=="__main__":
    with app.app_context():
        seed()
    print("Demo database seeded. Change all demo passwords before production.")
