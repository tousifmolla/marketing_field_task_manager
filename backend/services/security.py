"""Shared session validation and local secret provisioning."""
import json
import os
import secrets
from pathlib import Path
from flask_jwt_extended import get_jwt
from extensions import db, jwt
from models import User, RevokedToken
from utils.responses import error

KNOWN_ROLES = ("ADMIN", "MANAGER", "HR_ACCOUNTS", "MARKETING_EXECUTIVE")

def configure_security(app):
    if not app.config.get("TESTING"):
        path = Path(app.instance_path) / "security.json"
        if not path.exists():
            generated = {key: secrets.token_hex(32) for key in ("SECRET_KEY", "JWT_SECRET_KEY")}
            try:
                descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                pass
            else:
                with os.fdopen(descriptor, "w") as stream:
                    json.dump(generated, stream)
        stored = json.loads(path.read_text())
        for key in ("SECRET_KEY", "JWT_SECRET_KEY"):
            value = app.config.get(key) or stored[key]
            if not isinstance(value, str) or len(value) < 32 or value.startswith(("dev-", "replace-")):
                raise RuntimeError(f"Configure a strong {key} of at least 32 characters")
            app.config[key] = value
    app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
    @app.after_request
    def private_api(response):
        from flask import request
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

@jwt.user_lookup_loader
def lookup(_header, claims):
    identity = claims.get("sub")
    if not isinstance(identity, str) or not identity.isdecimal():
        return None
    user = db.session.get(User, int(identity))
    if not user or not user.active or user.role.name not in KNOWN_ROLES or user.employee and not user.employee.active:
        return None
    return user

@jwt.user_lookup_error_loader
def unavailable(_header, _claims):
    return error("Account is unavailable or inactive", 403)

@jwt.token_in_blocklist_loader
def revoked(_header, claims):
    return db.session.get(RevokedToken, claims["jti"]) is not None

@jwt.revoked_token_loader
def revoked_response(_header, _claims):
    return error("Session ended. Please sign in again.", 401)

@jwt.invalid_token_loader
def invalid(_reason):
    return error("Invalid session. Please sign in again.", 401)

@jwt.expired_token_loader
def expired(_header, _claims):
    return error("Session expired. Please sign in again.", 401)

def revoke_current():
    claims = get_jwt()
    if db.session.get(RevokedToken, claims["jti"]) is None:
        db.session.add(RevokedToken(jti=claims["jti"], expires_at=claims["exp"]))
    db.session.commit()
