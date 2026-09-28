from datetime import date, timezone
import math
from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import IntegrityError
from extensions import db
from middleware.auth import current_user, roles_required
from models import Attendance, EmployeeLocation, utcnow
from services.activity_service import record_activity
from utils.responses import error, success

bp = Blueprint("attendance", __name__, url_prefix="/api/attendance")


def timestamp(value):
    # SQLite drops timezone metadata; all persisted attendance times are UTC.
    return value.replace(tzinfo=timezone.utc).isoformat() if value else None


def serialize(row):
    return {
        "id": row.id, "employee_id": row.employee_id, "date": row.work_date.isoformat(),
        "check_in": timestamp(row.check_in), "check_out": timestamp(row.check_out),
        "check_in_lat": row.check_in_lat, "check_in_lng": row.check_in_lng,
        "check_in_accuracy": row.check_in_accuracy, "check_out_lat": row.check_out_lat,
        "check_out_lng": row.check_out_lng, "check_out_accuracy": row.check_out_accuracy,
        "working_minutes": row.working_minutes, "status": row.status,
        "is_active": bool(row.check_in and not row.check_out),
    }


def employee_or_error():
    user = current_user()
    return user.employee if user else None


def gps(payload):
    if not isinstance(payload, dict):
        raise ValueError("Valid GPS coordinates are required")
    values = []
    for key, low, high in (("latitude", -90, 90), ("longitude", -180, 180), ("accuracy", 0, float("inf"))):
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError("Valid GPS latitude, longitude and accuracy are required")
        values.append(value)
    return values


def active(employee_id):
    return Attendance.query.filter_by(employee_id=employee_id, check_out=None).filter(Attendance.check_in.isnot(None)).order_by(Attendance.work_date.desc()).first()


@bp.post("/check-in")
@jwt_required()
def check_in():
    employee = employee_or_error()
    if not employee:
        return error("No employee profile linked", 400)
    if active(employee.id) or Attendance.query.filter_by(employee_id=employee.id, work_date=date.today()).first():
        return error("Already checked in today or an earlier check-in is still active", 409)
    try:
        lat, lng, accuracy = gps(request.get_json(silent=True))
    except ValueError as exc:
        return error(str(exc), 422)
    now = utcnow()
    row = Attendance(employee_id=employee.id, work_date=date.today(), check_in=now,
                     check_in_lat=lat, check_in_lng=lng, check_in_accuracy=accuracy, status="Present")
    db.session.add(row)
    db.session.add(EmployeeLocation(employee_id=employee.id, latitude=lat, longitude=lng,
                                   accuracy=accuracy, activity_type="attendance_check_in", captured_at=now))
    record_activity(employee.id, "CHECK_IN", "Checked in for work")
    try:
        db.session.commit()
    except IntegrityError:
        # The unique employee/day constraint also handles concurrent requests.
        db.session.rollback()
        return error("Already checked in today", 409)
    return success(serialize(row), "Checked in", 201)


@bp.post("/check-out")
@jwt_required()
def check_out():
    employee = employee_or_error()
    row = active(employee.id) if employee else None
    if not row:
        return error("No active check-in. Refresh your attendance status", 409)
    try:
        lat, lng, accuracy = gps(request.get_json(silent=True))
    except ValueError as exc:
        return error(str(exc), 422)
    now = utcnow()
    # Only one concurrent checkout may close this record and create activity.
    changed = Attendance.query.filter_by(id=row.id, check_out=None).update({
        "check_out": now, "check_out_lat": lat, "check_out_lng": lng, "check_out_accuracy": accuracy,
    }, synchronize_session=False)
    if changed != 1:
        db.session.rollback()
        return error("Already checked out. Refresh your attendance status", 409)
    db.session.add(EmployeeLocation(employee_id=employee.id, latitude=lat, longitude=lng,
                                   accuracy=accuracy, activity_type="attendance_check_out", captured_at=now))
    record_activity(employee.id, "CHECK_OUT", "Checked out from work")
    db.session.commit()
    db.session.refresh(row)
    return success(serialize(row), "Checked out")


@bp.get("/today")
@jwt_required()
def today():
    employee = employee_or_error()
    if not employee:
        return error("No employee profile linked", 400)
    row = Attendance.query.filter_by(employee_id=employee.id, work_date=date.today()).first()
    current = active(employee.id)
    return success({"date": date.today().isoformat(), "record": serialize(row) if row else None,
                    "active": serialize(current) if current else None})


@bp.get("/me")
@jwt_required()
def mine():
    employee = employee_or_error()
    rows = Attendance.query.filter_by(employee_id=employee.id).order_by(Attendance.work_date.desc()).all() if employee else []
    return success([serialize(row) for row in rows])


@bp.get("")
@roles_required("ADMIN", "MANAGER", "HR_ACCOUNTS")
def all_attendance():
    return success([dict(serialize(row), employee=row.employee.name)
                    for row in Attendance.query.order_by(Attendance.work_date.desc()).all()])
