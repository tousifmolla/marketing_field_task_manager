from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from extensions import db
from middleware.auth import current_user, roles_required
from models import EmployeeLocation
from utils.responses import error, success

bp=Blueprint("location",__name__,url_prefix="/api/location")
def dump(x): return {"id":x.id,"latitude":x.latitude,"longitude":x.longitude,"accuracy":x.accuracy,"activity_type":x.activity_type,"captured_at":x.captured_at.isoformat(),"employee":x.employee.name}
@bp.post("/update")
@jwt_required()
def update():
    user=current_user(); p=request.get_json(silent=True) or {}
    if not user.employee: return error("No employee profile",400)
    if p.get("latitude") is None or p.get("longitude") is None: return error("Latitude and longitude are required",422)
    row=EmployeeLocation(employee_id=user.employee.id,latitude=float(p["latitude"]),longitude=float(p["longitude"]),accuracy=p.get("accuracy"),activity_type=p.get("activity_type","explicit_update")); db.session.add(row); db.session.commit(); return success(dump(row),"Location recorded",201)
@bp.get("/me")
@jwt_required()
def mine():
    user=current_user(); rows=EmployeeLocation.query.filter_by(employee_id=user.employee.id).order_by(EmployeeLocation.captured_at.desc()).limit(100).all() if user.employee else []; return success([dump(x) for x in rows])
@bp.get("/latest")
@roles_required("ADMIN","MANAGER")
def latest():
    rows=EmployeeLocation.query.order_by(EmployeeLocation.captured_at.desc()).all(); seen=set(); output=[]
    for row in rows:
        if row.employee_id not in seen: output.append(dump(row)); seen.add(row.employee_id)
    return success(output)
