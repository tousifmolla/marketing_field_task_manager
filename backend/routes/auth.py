from flask import Blueprint, request
from flask_jwt_extended import create_access_token, get_jti, jwt_required
from extensions import db
from middleware.auth import current_user
from models import AuditLog, User
from utils.responses import error, success

bp=Blueprint("auth",__name__,url_prefix="/api/auth")

def user_data(user): return {"id":user.id,"username":user.username,"role":user.role.name,"employee":{"id":user.employee.id,"code":user.employee.employee_code,"name":user.employee.name} if user.employee else None}

@bp.post("/login")
def login():
    payload=request.get_json(silent=True)
    if not isinstance(payload, dict) or not isinstance(payload.get("username"), str) or not isinstance(payload.get("password"), str):
        return error("Username and password are required", 422)
    user=User.query.filter_by(username=payload["username"].strip()).first()
    if not user or not user.active or (user.employee and not user.employee.active) or not user.verify_password(payload.get("password", "")): return error("Invalid username or password",401)
    token=create_access_token(identity=str(user.id),additional_claims={"role":user.role.name})
    db.session.add(AuditLog(user_id=user.id,action="LOGIN",entity_type="user",entity_id=str(user.id))); db.session.commit()
    return success({"access_token":token,"user":user_data(user)},"Login successful")

@bp.get("/me")
@jwt_required()
def me(): return success(user_data(current_user()))

@bp.post("/logout")
@jwt_required()
def logout():
    from services.security import revoke_current
    revoke_current()
    return success(message="Session ended")
