from uuid import uuid4
from flask import Blueprint, request
from extensions import db
from middleware.auth import current_user, roles_required
from models import Appointment
from models.core import utcnow
from services.activity_service import record_activity, audit
from services.field_validation import FIELD_ROLES, validated, payload, text, executive, client, instant, iso
from utils.responses import error, success

bp = Blueprint("appointments", __name__, url_prefix="/api/appointments")

def dump(x):
    return {"id": x.id, "appointment_code": x.appointment_code, "client_id": x.client_id,
            "client": x.client.business_name, "employee_id": x.employee_id,
            "appointment_at": iso(x.appointment_at), "purpose": x.purpose,
            "address": x.address, "status": x.status, "notes": x.remarks, "remarks": x.remarks,
            "created_at": iso(x.created_at), "updated_at": iso(x.updated_at)}

def allowed(user, row):
    return user.role.name in ("ADMIN", "MANAGER") or bool(user.employee and user.employee.active and row.employee_id == user.employee.id)

@bp.get("/clients")
@roles_required(*FIELD_ROLES)
def choices():
    from models import Client
    # Client catalogue is shared, matching the existing client module.
    return success([{"id": x.id, "business_name": x.business_name} for x in Client.query.order_by(Client.business_name).all()])

@bp.get("/me")
@roles_required(*FIELD_ROLES)
def mine():
    user = current_user()
    if not user.employee or not user.employee.active:
        return success([])
    query = Appointment.query.filter_by(employee_id=user.employee.id)
    if request.args.get("upcoming") == "true":
        query = query.filter(Appointment.status == "Scheduled", Appointment.appointment_at >= utcnow())
    return success([dump(x) for x in query.order_by(Appointment.appointment_at, Appointment.id).all()])

@bp.get("")
@roles_required("ADMIN", "MANAGER")
def all_appointments():
    return success([dump(x) for x in Appointment.query.order_by(Appointment.appointment_at).all()])

@bp.get("/<int:item_id>")
@roles_required(*FIELD_ROLES)
def detail(item_id):
    row = db.get_or_404(Appointment, item_id)
    return success(dump(row)) if allowed(current_user(), row) else error("You cannot access this appointment", 403)

def fields(p):
    values = {}
    if "client_id" in p:
        values["client_id"] = client(p["client_id"]).id
    if "appointment_at" in p:
        values["appointment_at"] = instant(p["appointment_at"])
    for key, limit in (("purpose", 180), ("address", 2000)):
        if key in p:
            values[key] = text(p, key, limit)
    if "notes" in p or "remarks" in p:
        values["remarks"] = text(p, "notes" if "notes" in p else "remarks")
    if "status" in p:
        if p["status"] not in ("Scheduled", "Completed", "Cancelled"):
            raise ValueError("Select Scheduled, Completed or Cancelled")
        values["status"] = p["status"]
    return values

@bp.post("")
@roles_required(*FIELD_ROLES)
@validated
def create():
    user = current_user()
    p = payload(("client_id", "appointment_at", "employee_id", "purpose", "address", "notes", "remarks"))
    if user.role.name in ("ADMIN", "MANAGER"):
        target = executive(p.get("employee_id"))
    else:
        if not user.employee or not user.employee.active:
            return error("An active executive profile is required", 403)
        target = user.employee
        if "employee_id" in p and p["employee_id"] != target.id:
            return error("You can create appointments only for yourself", 403)
    if "client_id" not in p or "appointment_at" not in p:
        raise ValueError("Client and appointment date/time are required")
    values = fields(p)
    row = Appointment(appointment_code=f"APT-{uuid4().hex[:24]}", employee_id=target.id, **values)
    db.session.add(row)
    db.session.flush()
    record_activity(target.id, "APPOINTMENT_CREATED", f"Created {row.appointment_code}", client_id=row.client_id)
    audit(user.id, "APPOINTMENT_CREATE", "appointment", row.id, iso(row.appointment_at))
    db.session.commit()
    return success(dump(row), "Appointment created", 201)

@bp.patch("/<int:item_id>")
@roles_required(*FIELD_ROLES)
@validated
def update(item_id):
    user = current_user()
    row = db.get_or_404(Appointment, item_id)
    if not allowed(user, row):
        return error("You cannot update this appointment", 403)
    p = payload(("client_id", "appointment_at", "purpose", "address", "notes", "remarks", "status"))
    if not p:
        raise ValueError("Enter appointment changes before saving")
    values = fields(p)
    for key, value in values.items():
        setattr(row, key, value)
    record_activity(row.employee_id, "APPOINTMENT_UPDATED", f"Updated {row.appointment_code}: {row.status}", client_id=row.client_id)
    audit(user.id, "APPOINTMENT_UPDATE", "appointment", row.id, ", ".join(sorted(p)))
    db.session.commit()
    return success(dump(row), "Appointment updated")
