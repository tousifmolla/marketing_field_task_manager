from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from werkzeug.utils import secure_filename
from extensions import db
from middleware.auth import current_user, roles_required
from models import Photo, Client, Task
from services.activity_service import record_activity
from services.photo_storage import prepare_photo, save_photo, remove_photo, photo_response
from utils.responses import error, success

bp = Blueprint("photos", __name__, url_prefix="/api/photos")

@bp.post("")
@roles_required("ADMIN", "MANAGER", "MARKETING_EXECUTIVE")
def upload():
    user = current_user()
    if not user.employee:
        return error("No employee profile", 400)
    file = request.files.get("photo")
    try:
        data, _ = prepare_photo(file)
    except ValueError as exc:
        return error(str(exc), 415)
    client_id = request.form.get("client_id", type=int)
    if client_id:
        client = db.session.get(Client, client_id)
        if not client:
            return error("Client not found", 404)
        if user.role.name not in ("ADMIN", "MANAGER", "HR_ACCOUNTS") and client.created_by != user.id:
            return error("You do not have permission to add this photo", 403)
    task_id = request.form.get("task_id", type=int)
    if request.form.get("task_id") and not task_id:
        return error("Select a valid task", 422)
    if task_id:
        task = db.get_or_404(Task, task_id)
        if user.role.name not in ("ADMIN", "MANAGER") and task.assigned_employee_id != user.employee.id:
            return error("You cannot attach a photo to this task", 403)
    name = None
    try:
        name = save_photo(data)
        row = Photo(employee_id=user.employee.id, client_id=client_id, task_id=task_id,
                    file_path=name, original_name=(secure_filename(file.filename) or "photo.jpg")[:180],
                    latitude=request.form.get("latitude", type=float), longitude=request.form.get("longitude", type=float),
                    remarks=request.form.get("remarks"))
        db.session.add(row)
        record_activity(user.employee.id, "PHOTO_UPLOADED", "Uploaded field photo", client_id=row.client_id, task_id=row.task_id)
        db.session.commit()
        return success({"id": row.id, "file_path": name, "url": f"/photos/{row.id}/file"}, "Photo uploaded", 201)
    except Exception:
        db.session.rollback()
        if name:
            remove_photo(name)
        raise

@bp.get("/<int:photo_id>/file")
@jwt_required()
def download(photo_id):
    row = db.get_or_404(Photo, photo_id)
    user = current_user()
    if user.role.name not in ("ADMIN", "MANAGER", "HR_ACCOUNTS") and (not user.employee or row.employee_id != user.employee.id):
        return error("You do not have permission to view this photo", 403)
    return photo_response(row.file_path)
