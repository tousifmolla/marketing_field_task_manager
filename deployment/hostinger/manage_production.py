"""Explicit production bootstrap. Never loads demo data or drops tables."""
import argparse
from getpass import getpass
from wsgi import application
from extensions import db
from models import Role, User, Employee

parser = argparse.ArgumentParser()
parser.add_argument("command", choices=("init-db", "create-admin"))
args = parser.parse_args()
with application.app_context():
    if args.command == "init-db":
        db.create_all()
        for name in ("ADMIN", "MANAGER", "HR_ACCOUNTS", "MARKETING_EXECUTIVE"):
            if not Role.query.filter_by(name=name).first():
                db.session.add(Role(name=name))
        db.session.commit()
        print("Missing tables and roles initialized. Existing records were preserved.")
    else:
        username = input("Administrator username: ").strip()
        employee_code = input("Administrator employee code: ").strip()
        name = input("Administrator display name: ").strip()
        password = getpass("Administrator password (12+ characters): ")
        confirm = getpass("Confirm password: ")
        if not username or not employee_code or not name or len(password) < 12 or password != confirm:
            raise SystemExit("Invalid input or passwords do not match; nothing was saved")
        if User.query.filter_by(username=username).first() or Employee.query.filter_by(employee_code=employee_code).first():
            raise SystemExit("Username or employee code already exists; nothing was changed")
        role = Role.query.filter_by(name="ADMIN").first()
        if role is None:
            raise SystemExit("Run init-db first")
        user = User(username=username, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        db.session.add(Employee(employee_code=employee_code, name=name, user_id=user.id, designation="Administrator"))
        db.session.commit()
        print("Administrator created. No credentials were printed or stored in source files.")
