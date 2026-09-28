from datetime import datetime, timezone
from werkzeug.security import check_password_hash, generate_password_hash
from extensions import db

def utcnow(): return datetime.now(timezone.utc)

class TimestampMixin:
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

class Role(db.Model):
    __tablename__="roles"; id=db.Column(db.Integer,primary_key=True); name=db.Column(db.String(40),unique=True,nullable=False)

class User(TimestampMixin, db.Model):
    __tablename__="users"; id=db.Column(db.Integer,primary_key=True); username=db.Column(db.String(80),unique=True,index=True,nullable=False); password_hash=db.Column(db.String(255),nullable=False); role_id=db.Column(db.Integer,db.ForeignKey("roles.id"),nullable=False); active=db.Column(db.Boolean,default=True,nullable=False); role=db.relationship("Role"); employee=db.relationship("Employee",back_populates="user",uselist=False)
    def set_password(self,value): self.password_hash=generate_password_hash(value)
    def verify_password(self,value): return check_password_hash(self.password_hash,value)

class Employee(TimestampMixin, db.Model):
    __tablename__="employees"; id=db.Column(db.Integer,primary_key=True); employee_code=db.Column(db.String(30),unique=True,index=True,nullable=False); user_id=db.Column(db.Integer,db.ForeignKey("users.id"),unique=True); manager_id=db.Column(db.Integer,db.ForeignKey("employees.id")); name=db.Column(db.String(120),nullable=False); email=db.Column(db.String(120)); phone=db.Column(db.String(15)); designation=db.Column(db.String(80)); basic_salary=db.Column(db.Numeric(12,2),default=0); active=db.Column(db.Boolean,default=True); user=db.relationship("User",back_populates="employee"); manager=db.relationship("Employee",remote_side=[id])

class Attendance(TimestampMixin, db.Model):
    __tablename__="attendance"; id=db.Column(db.Integer,primary_key=True); employee_id=db.Column(db.Integer,db.ForeignKey("employees.id"),nullable=False,index=True); work_date=db.Column(db.Date,nullable=False,index=True); check_in=db.Column(db.DateTime(timezone=True)); check_out=db.Column(db.DateTime(timezone=True)); check_in_lat=db.Column(db.Float); check_in_lng=db.Column(db.Float); check_in_accuracy=db.Column(db.Float); check_out_lat=db.Column(db.Float); check_out_lng=db.Column(db.Float); check_out_accuracy=db.Column(db.Float); status=db.Column(db.String(30),default="Present"); employee=db.relationship("Employee"); __table_args__=(db.UniqueConstraint("employee_id","work_date",name="uq_attendance_day"),)
    @property
    def working_minutes(self): return round((self.check_out-self.check_in).total_seconds()/60) if self.check_in and self.check_out else None

class EmployeeLocation(db.Model):
    __tablename__="employee_locations"; id=db.Column(db.Integer,primary_key=True); employee_id=db.Column(db.Integer,db.ForeignKey("employees.id"),nullable=False,index=True); latitude=db.Column(db.Float,nullable=False); longitude=db.Column(db.Float,nullable=False); accuracy=db.Column(db.Float); activity_type=db.Column(db.String(50),nullable=False); captured_at=db.Column(db.DateTime(timezone=True),default=utcnow,index=True); employee=db.relationship("Employee")

class Client(TimestampMixin, db.Model):
    __tablename__="clients"; id=db.Column(db.Integer,primary_key=True); client_code=db.Column(db.String(30),unique=True,index=True,nullable=False); business_name=db.Column(db.String(160),nullable=False); contact_person=db.Column(db.String(120),nullable=False); mobile=db.Column(db.String(10),nullable=False); alternate_mobile=db.Column(db.String(10)); email=db.Column(db.String(120)); address=db.Column(db.Text,nullable=False); city=db.Column(db.String(80)); district=db.Column(db.String(80)); state=db.Column(db.String(80)); pin_code=db.Column(db.String(6)); latitude=db.Column(db.Float); longitude=db.Column(db.Float); business_type=db.Column(db.String(80)); gst_number=db.Column(db.String(20)); interested_product=db.Column(db.String(120)); expected_order_value=db.Column(db.Numeric(12,2)); remarks=db.Column(db.Text); photo_path=db.Column(db.String(255)); created_by=db.Column(db.Integer,db.ForeignKey("users.id"),nullable=False,index=True); creator=db.relationship("User")

class ClientVisit(TimestampMixin, db.Model):
    __tablename__="client_visits"; id=db.Column(db.Integer,primary_key=True); client_id=db.Column(db.Integer,db.ForeignKey("clients.id"),nullable=False); employee_id=db.Column(db.Integer,db.ForeignKey("employees.id"),nullable=False,index=True); visit_at=db.Column(db.DateTime(timezone=True),default=utcnow); latitude=db.Column(db.Float); longitude=db.Column(db.Float); purpose=db.Column(db.String(160)); notes=db.Column(db.Text); result=db.Column(db.String(160)); follow_up_required=db.Column(db.Boolean,default=False); follow_up_date=db.Column(db.Date); photo_path=db.Column(db.String(255)); status=db.Column(db.String(30),default="Scheduled"); client=db.relationship("Client"); employee=db.relationship("Employee")

class Task(TimestampMixin, db.Model):
    __tablename__="tasks"; id=db.Column(db.Integer,primary_key=True); task_code=db.Column(db.String(30),unique=True,index=True,nullable=False); title=db.Column(db.String(160),nullable=False); description=db.Column(db.Text); assigned_employee_id=db.Column(db.Integer,db.ForeignKey("employees.id"),nullable=False,index=True); assigned_by=db.Column(db.Integer,db.ForeignKey("users.id"),nullable=False); client_id=db.Column(db.Integer,db.ForeignKey("clients.id")); location=db.Column(db.String(200)); priority=db.Column(db.String(20),default="Medium"); start_date=db.Column(db.Date); deadline=db.Column(db.Date,index=True); instructions=db.Column(db.Text); status=db.Column(db.String(30),default="Not Started"); assigned_employee=db.relationship("Employee"); client=db.relationship("Client")

class TaskUpdate(db.Model):
    __tablename__="task_updates"; id=db.Column(db.Integer,primary_key=True); task_id=db.Column(db.Integer,db.ForeignKey("tasks.id"),nullable=False,index=True); user_id=db.Column(db.Integer,db.ForeignKey("users.id"),nullable=False); status=db.Column(db.String(30)); remarks=db.Column(db.Text); proof_path=db.Column(db.String(255)); created_at=db.Column(db.DateTime(timezone=True),default=utcnow); task=db.relationship("Task")

class Appointment(TimestampMixin, db.Model):
    __tablename__="appointments"; id=db.Column(db.Integer,primary_key=True); appointment_code=db.Column(db.String(30),unique=True,nullable=False); client_id=db.Column(db.Integer,db.ForeignKey("clients.id"),nullable=False); employee_id=db.Column(db.Integer,db.ForeignKey("employees.id"),nullable=False,index=True); appointment_at=db.Column(db.DateTime(timezone=True),nullable=False,index=True); purpose=db.Column(db.String(180)); address=db.Column(db.Text); latitude=db.Column(db.Float); longitude=db.Column(db.Float); remarks=db.Column(db.Text); status=db.Column(db.String(30),default="Scheduled"); client=db.relationship("Client"); employee=db.relationship("Employee")

class Photo(db.Model):
    __tablename__="photos"; id=db.Column(db.Integer,primary_key=True); employee_id=db.Column(db.Integer,db.ForeignKey("employees.id"),nullable=False,index=True); client_id=db.Column(db.Integer,db.ForeignKey("clients.id")); task_id=db.Column(db.Integer,db.ForeignKey("tasks.id")); file_path=db.Column(db.String(255),nullable=False); original_name=db.Column(db.String(180)); latitude=db.Column(db.Float); longitude=db.Column(db.Float); remarks=db.Column(db.Text); captured_at=db.Column(db.DateTime(timezone=True),default=utcnow)

class Activity(db.Model):
    __tablename__="activities"; id=db.Column(db.Integer,primary_key=True); employee_id=db.Column(db.Integer,db.ForeignKey("employees.id"),nullable=False,index=True); activity_type=db.Column(db.String(60),nullable=False,index=True); description=db.Column(db.String(255),nullable=False); client_id=db.Column(db.Integer,db.ForeignKey("clients.id")); task_id=db.Column(db.Integer,db.ForeignKey("tasks.id")); occurred_at=db.Column(db.DateTime(timezone=True),default=utcnow,index=True)

class Payroll(TimestampMixin, db.Model):
    __tablename__="payroll"; id=db.Column(db.Integer,primary_key=True); employee_id=db.Column(db.Integer,db.ForeignKey("employees.id"),nullable=False,index=True); year=db.Column(db.Integer,nullable=False); month=db.Column(db.Integer,nullable=False); basic_salary=db.Column(db.Numeric(12,2),default=0); working_days=db.Column(db.Integer,default=0); present_days=db.Column(db.Integer,default=0); leave_days=db.Column(db.Integer,default=0); absent_days=db.Column(db.Integer,default=0); overtime=db.Column(db.Numeric(12,2),default=0); ta_da=db.Column(db.Numeric(12,2),default=0); sales_incentive=db.Column(db.Numeric(12,2),default=0); other_incentive=db.Column(db.Numeric(12,2),default=0); deductions=db.Column(db.Numeric(12,2),default=0); net_salary=db.Column(db.Numeric(12,2),default=0); published=db.Column(db.Boolean,default=False); employee=db.relationship("Employee"); __table_args__=(db.UniqueConstraint("employee_id","year","month",name="uq_payroll_month"),)

class Product(TimestampMixin, db.Model):
    __tablename__="products"; id=db.Column(db.Integer,primary_key=True); product_code=db.Column(db.String(30),unique=True,nullable=False); product_name=db.Column(db.String(160),nullable=False); category=db.Column(db.String(80)); price=db.Column(db.Numeric(12,2),nullable=False); status=db.Column(db.String(20),default="Active")
class Order(TimestampMixin, db.Model):
    __tablename__="orders"; id=db.Column(db.Integer,primary_key=True); order_number=db.Column(db.String(30),unique=True,nullable=False); client_id=db.Column(db.Integer,db.ForeignKey("clients.id"),nullable=False); executive_id=db.Column(db.Integer,db.ForeignKey("employees.id"),nullable=False); order_date=db.Column(db.Date,nullable=False); amount=db.Column(db.Numeric(12,2),default=0); status=db.Column(db.String(20),default="Draft"); client=db.relationship("Client"); items=db.relationship("OrderItem",cascade="all, delete-orphan")
class OrderItem(db.Model):
    __tablename__="order_items"; id=db.Column(db.Integer,primary_key=True); order_id=db.Column(db.Integer,db.ForeignKey("orders.id"),nullable=False); product_id=db.Column(db.Integer,db.ForeignKey("products.id"),nullable=False); quantity=db.Column(db.Integer,nullable=False); unit_price=db.Column(db.Numeric(12,2),nullable=False); product=db.relationship("Product")
class Expense(TimestampMixin, db.Model):
    __tablename__="expenses"; id=db.Column(db.Integer,primary_key=True); employee_id=db.Column(db.Integer,db.ForeignKey("employees.id")); category=db.Column(db.String(80)); amount=db.Column(db.Numeric(12,2),nullable=False); expense_date=db.Column(db.Date,nullable=False); description=db.Column(db.Text)
class Notification(db.Model):
    __tablename__="notifications"; id=db.Column(db.Integer,primary_key=True); user_id=db.Column(db.Integer,db.ForeignKey("users.id"),nullable=False,index=True); title=db.Column(db.String(150),nullable=False); message=db.Column(db.Text,nullable=False); notification_type=db.Column(db.String(50)); is_read=db.Column(db.Boolean,default=False,index=True); created_at=db.Column(db.DateTime(timezone=True),default=utcnow,index=True)
class AuditLog(db.Model):
    __tablename__="audit_logs"; id=db.Column(db.Integer,primary_key=True); user_id=db.Column(db.Integer,db.ForeignKey("users.id"),index=True); action=db.Column(db.String(80),nullable=False); entity_type=db.Column(db.String(80)); entity_id=db.Column(db.String(40)); details=db.Column(db.Text); timestamp=db.Column(db.DateTime(timezone=True),default=utcnow,index=True)

class ClientOnboardingRequest(db.Model):
    __tablename__ = "client_onboarding_requests"
    id = db.Column(db.String(64), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False)
    request_hash = db.Column(db.String(64), nullable=False)

class RevokedToken(db.Model):
    __tablename__ = "revoked_tokens"
    jti = db.Column(db.String(64), primary_key=True)
    expires_at = db.Column(db.Integer, nullable=False)
