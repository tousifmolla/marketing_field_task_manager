from datetime import date
from uuid import uuid4
from flask import Blueprint, request
from sqlalchemy import update as sql_update
from extensions import db
from middleware.auth import current_user, roles_required
from models import Notification, Task, TaskUpdate, Employee
from models.core import utcnow
from services.activity_service import audit, record_activity
from services.field_validation import FIELD_ROLES, validated, payload, text, executive, client, day, iso, identifier
from utils.responses import error, success

bp = Blueprint("tasks", __name__, url_prefix="/api/tasks")
NEXT = {"Pending": "In Progress", "In Progress": "Completed"}

def status(task):
    return "Pending" if task.status == "Not Started" else task.status

def history(task):
    return TaskUpdate.query.filter_by(task_id=task.id).order_by(TaskUpdate.created_at, TaskUpdate.id).all()

def dump(task, detail=False):
    updates = history(task)
    result = {key: getattr(task, key) for key in ("id", "task_code", "title", "description", "assigned_employee_id", "assigned_by", "client_id", "location", "priority", "instructions")}
    result.update(status=status(task), client=task.client.business_name if task.client else None,
                  executive=task.assigned_employee.name, start_date=task.start_date.isoformat() if task.start_date else None,
                  deadline=task.deadline.isoformat() if task.deadline else None,
                  created_at=iso(task.created_at), updated_at=iso(task.updated_at),
                  started_at=next((iso(x.created_at) for x in updates if x.status == "In Progress"), None),
                  completed_at=next((iso(x.created_at) for x in updates if x.status == "Completed"), None))
    if detail:
        result["history"] = [{"id": x.id, "status": x.status, "user_id": x.user_id, "remarks": x.remarks, "created_at": iso(x.created_at)} for x in updates]
    return result

def can_access(user, task):
    return user.role.name in ("ADMIN", "MANAGER") or bool(user.employee and user.employee.active and task.assigned_employee_id == user.employee.id)

@bp.get("/executives")
@roles_required("ADMIN", "MANAGER")
def executives():
    rows = Employee.query.filter_by(active=True).all()
    return success([{"id": x.id, "name": x.name} for x in rows if x.user and x.user.active and x.user.role.name == "MARKETING_EXECUTIVE"])

@bp.get("")
@roles_required("ADMIN", "MANAGER")
@validated
def all_tasks():
    query = Task.query
    if request.args.get("employee_id"):
        try:
            employee_id = int(request.args["employee_id"])
        except ValueError:
            raise ValueError("Select a valid executive") from None
        query = query.filter_by(assigned_employee_id=identifier(employee_id, "executive"))
    return success([dump(x) for x in query.order_by(Task.created_at.desc(), Task.id.desc()).all()])

@bp.get("/me")
@roles_required(*FIELD_ROLES)
def mine():
    user = current_user()
    rows = Task.query.filter_by(assigned_employee_id=user.employee.id).order_by(Task.deadline, Task.id.desc()).all() if user.employee and user.employee.active else []
    return success([dump(x) for x in rows])

@bp.get("/<int:task_id>")
@roles_required(*FIELD_ROLES)
def get_task(task_id):
    task = db.get_or_404(Task, task_id)
    return success(dump(task, True)) if can_access(current_user(), task) else error("You cannot access this task", 403)

@bp.get("/<int:task_id>/history")
@roles_required(*FIELD_ROLES)
def task_history(task_id):
    task = db.get_or_404(Task, task_id)
    return success(dump(task, True)["history"]) if can_access(current_user(), task) else error("You cannot access this task", 403)

@bp.post("")
@roles_required("ADMIN", "MANAGER")
@validated
def create():
    user = current_user()
    p = payload(("title", "description", "assigned_employee_id", "client_id", "location", "priority", "start_date", "deadline", "instructions"))
    target = executive(p.get("assigned_employee_id"))
    title = text(p, "title", 160, True)
    priority = p.get("priority", "Medium")
    if priority not in ("Low", "Medium", "High"):
        raise ValueError("Select Low, Medium or High priority")
    start = day(p.get("start_date")) or date.today()
    deadline = day(p.get("deadline"))
    if deadline and deadline < start:
        raise ValueError("Deadline must be on or after the start date")
    task = Task(task_code=f"TSK-{uuid4().hex[:24]}", title=title,
                assigned_employee_id=target.id, assigned_by=user.id, status="Pending",
                client_id=client(p["client_id"]).id if p.get("client_id") is not None else None,
                description=text(p, "description"), location=text(p, "location", 200),
                instructions=text(p, "instructions"), priority=priority, start_date=start, deadline=deadline)
    db.session.add(task)
    db.session.flush()
    db.session.add(TaskUpdate(task_id=task.id, user_id=user.id, status="Pending", remarks="Task assigned"))
    db.session.add(Notification(user_id=target.user.id, title="New task assigned", message=title, notification_type="task"))
    record_activity(target.id, "TASK_ASSIGNED", f"Assigned {task.task_code}: {title}", task_id=task.id)
    audit(user.id, "TASK_ASSIGN", "task", task.id, title)
    db.session.commit()
    return success(dump(task, True), "Task assigned", 201)

def change(task_id, updates=False):
    user = current_user()
    task = db.get_or_404(Task, task_id)
    if not can_access(user, task):
        return error("You cannot update this task", 403)
    p = payload(("status", "remarks"))
    requested = p.get("status")
    if requested not in ("Pending", "In Progress", "Completed"):
        raise ValueError("Select Pending, In Progress or Completed")
    remarks = text(p, "remarks")
    previous = status(task)
    if requested == previous:
        return success(dump(task, True), "Task is already at this status")
    if NEXT.get(previous) != requested:
        return error("Start the pending task before completing it. Completed tasks cannot be reopened.", 409)
    original = task.status
    changed = db.session.execute(sql_update(Task).where(Task.id == task.id, Task.status == original).values(status=requested, updated_at=utcnow()).execution_options(synchronize_session=False))
    if changed.rowcount != 1:
        db.session.rollback()
        return error("The task changed. Refresh and try again.", 409)
    db.session.add(TaskUpdate(task_id=task.id, user_id=user.id, status=requested, remarks=remarks or f"{previous} → {requested}"))
    record_activity(task.assigned_employee_id, "TASK_STATUS_CHANGE", f"{task.task_code}: {previous} → {requested}", task_id=task.id)
    audit(user.id, "TASK_STATUS_CHANGE", "task", task.id, f"{previous} → {requested}")
    db.session.commit()
    return success(dump(task, True), "Task status saved", 201 if updates else 200)

@bp.patch("/<int:task_id>")
@roles_required(*FIELD_ROLES)
@validated
def update(task_id):
    return change(task_id)

@bp.post("/<int:task_id>/updates")
@roles_required(*FIELD_ROLES)
@validated
def add_update(task_id):
    return change(task_id, True)
