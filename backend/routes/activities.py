from flask import Blueprint, request
from middleware.auth import current_user, roles_required
from models import Activity
from services.field_validation import FIELD_ROLES, iso
from utils.responses import success

bp = Blueprint("activities", __name__, url_prefix="/api/activities")

def rows(employee_id):
    query = Activity.query.filter_by(employee_id=employee_id)
    if request.args.get("type"):
        query = query.filter_by(activity_type=request.args["type"])
    return [{"id": x.id, "employee_id": x.employee_id, "type": x.activity_type,
             "description": x.description, "occurred_at": iso(x.occurred_at),
             "client_id": x.client_id, "task_id": x.task_id}
            for x in query.order_by(Activity.occurred_at.desc(), Activity.id.desc()).limit(500).all()]

@bp.get("/me")
@roles_required(*FIELD_ROLES)
def mine():
    user = current_user()
    return success(rows(user.employee.id) if user.employee and user.employee.active else [])

@bp.get("/employees/<int:employee_id>")
@roles_required("ADMIN", "MANAGER")
def employee_history(employee_id):
    from extensions import db
    from models import Employee
    db.get_or_404(Employee, employee_id)
    return success(rows(employee_id))
