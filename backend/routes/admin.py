import csv
import io
from functools import wraps
from datetime import date
from flask import Blueprint, Response, redirect, render_template, request, session, url_for
from flask_jwt_extended import jwt_required
from extensions import db
from middleware.auth import current_user, roles_required
from models import Appointment, Attendance, AuditLog, Client, Employee, Role, Task, User
from services.activity_service import audit
from utils.responses import error, success
bp=Blueprint("admin",__name__)
def web_roles(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args,**kwargs):
            user=db.session.get(User,session.get("user_id")) if session.get("user_id") else None
            if not user or not user.active or (user.employee and not user.employee.active) or user.role.name not in roles:return redirect(url_for("admin.web_login"))
            return fn(*args,**kwargs)
        return wrapper
    return decorator
@bp.route("/admin/login",methods=["GET","POST"])
def web_login():
    message=None
    if request.method=="POST":
        user=User.query.filter_by(username=request.form.get("username","").strip()).first()
        if user and user.active and (not user.employee or user.employee.active) and user.role.name in ("ADMIN","MANAGER","HR_ACCOUNTS") and user.verify_password(request.form.get("password","")):
            session["user_id"]=user.id;return redirect(url_for("admin.dashboard"))
        message="Invalid dashboard credentials"
    return render_template("login.html",message=message)
@bp.get("/admin/logout")
def web_logout():session.clear();return redirect(url_for("admin.web_login"))
@bp.get("/admin")
@web_roles("ADMIN","MANAGER","HR_ACCOUNTS")
def dashboard():
    kpis={"employees":Employee.query.filter_by(active=True).count(),"present":Attendance.query.filter_by(work_date=date.today(),status="Present").count(),"active_tasks":Task.query.filter(Task.status.in_(["Pending","Not Started","In Progress"])).count(),"overdue":Task.query.filter(Task.deadline<date.today(),Task.status!="Completed").count(),"appointments":Appointment.query.filter(db.func.date(Appointment.appointment_at)==date.today()).count(),"clients":Client.query.count()}; return render_template("dashboard.html",kpis=kpis,tasks=Task.query.order_by(Task.created_at.desc()).limit(5).all())
@bp.get("/api/admin/dashboard")
@roles_required("ADMIN","MANAGER","HR_ACCOUNTS")
def dashboard_api():return success({"total_employees":Employee.query.count(),"present_today":Attendance.query.filter_by(work_date=date.today(),status="Present").count(),"active_tasks":Task.query.filter(Task.status!="Completed").count(),"appointments_today":Appointment.query.filter(db.func.date(Appointment.appointment_at)==date.today()).count(),"new_clients":Client.query.count()})
@bp.post("/api/admin/users")
@roles_required("ADMIN")
def create_user():
    u=current_user(); p=request.get_json(silent=True) or {}; role=Role.query.filter_by(name=p.get("role")).first()
    if not role or not p.get("username") or not p.get("password"):return error("Username, password and valid role required",422)
    if User.query.filter_by(username=p["username"]).first():return error("Username already exists",409)
    row=User(username=p["username"],role=role); row.set_password(p["password"]); db.session.add(row); db.session.flush(); audit(u.id,"USER_CREATE","user",row.id,row.username); db.session.commit(); return success({"id":row.id,"username":row.username,"role":role.name},"User created",201)
@bp.get("/api/admin/audit-logs")
@roles_required("ADMIN")
def audit_logs():return success([{"id":x.id,"user_id":x.user_id,"action":x.action,"entity_type":x.entity_type,"entity_id":x.entity_id,"details":x.details,"timestamp":x.timestamp.isoformat()} for x in AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(500).all()])
@bp.get("/api/admin/reports/attendance.csv")
@roles_required("ADMIN","MANAGER","HR_ACCOUNTS")
def attendance_csv():
    stream=io.StringIO(); writer=csv.writer(stream); writer.writerow(["Employee","Date","Status","Check In","Check Out","Minutes"])
    for x in Attendance.query.order_by(Attendance.work_date.desc()).all():writer.writerow([x.employee.name,x.work_date,x.status,x.check_in,x.check_out,x.working_minutes])
    return Response(stream.getvalue(),mimetype="text/csv",headers={"Content-Disposition":"attachment; filename=attendance.csv"})

@bp.get("/admin/clients")
@web_roles("ADMIN", "MANAGER", "HR_ACCOUNTS")
def web_clients():
    return render_template("clients.html", clients=Client.query.order_by(Client.created_at.desc()).all())


@bp.get("/admin/clients/<int:client_id>")
@web_roles("ADMIN", "MANAGER", "HR_ACCOUNTS")
def web_client(client_id):
    from models import Photo
    client = db.get_or_404(Client, client_id)
    return render_template("client_detail.html", client=client, photos=Photo.query.filter_by(client_id=client.id).all())


@bp.get("/admin/photos/<int:photo_id>")
@web_roles("ADMIN", "MANAGER", "HR_ACCOUNTS")
def web_photo(photo_id):
    from models import Photo
    from services.photo_storage import photo_response
    return photo_response(db.get_or_404(Photo, photo_id).file_path)

@bp.get("/admin/field-work")
@web_roles("ADMIN", "MANAGER")
def web_field_work():
    from flask_jwt_extended import create_access_token
    return render_template("field_work.html", field_token=create_access_token(identity=str(session["user_id"])))
