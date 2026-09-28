from functools import wraps
from flask_jwt_extended import get_jwt_identity, jwt_required
from extensions import db
from models import User
from utils.responses import error

def current_user(): return db.session.get(User,int(get_jwt_identity()))

def roles_required(*roles):
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            user=current_user()
            if not user or not user.active: return error("Account is inactive",403)
            if user.role.name not in roles: return error("You do not have permission for this action",403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator
