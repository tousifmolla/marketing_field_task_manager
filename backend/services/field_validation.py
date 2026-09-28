from datetime import date, datetime, timezone
from functools import wraps
from flask import request
from extensions import db
from models import Employee, Client
from utils.responses import error

FIELD_ROLES = ("ADMIN", "MANAGER", "MARKETING_EXECUTIVE")

def validated(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ValueError as exc:
            db.session.rollback()
            return error(str(exc), 422)
    return wrapped

def payload(allowed):
    p = request.get_json(silent=True)
    if not isinstance(p, dict):
        raise ValueError("Send a valid JSON object")
    if set(p) - set(allowed):
        raise ValueError("One or more fields cannot be changed")
    return p

def text(p, key, limit=2000, required=False):
    value = p.get(key)
    if value is None and not required:
        return None
    if not isinstance(value, str) or (required and not value.strip()) or len(value.strip()) > limit:
        raise ValueError(f"Enter a valid {key.replace('_', ' ')} (up to {limit} characters)")
    return value.strip()

def identifier(value, label):
    if type(value) is not int or value <= 0:
        raise ValueError(f"Select a valid {label}")
    return value

def executive(value):
    row = db.session.get(Employee, identifier(value, "executive"))
    if not row or not row.active or not row.user or not row.user.active or row.user.role.name != "MARKETING_EXECUTIVE":
        raise ValueError("Select an active marketing executive")
    return row

def client(value):
    row = db.session.get(Client, identifier(value, "client"))
    if not row:
        raise ValueError("Select an existing client")
    return row

def day(value):
    if value is None or value == "":
        return None
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        raise ValueError("Enter a valid date (YYYY-MM-DD)") from None

def instant(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        # Older clients sent timezone-free UTC. New clients always send an offset.
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Enter a valid appointment date and time") from None

def iso(value):
    return value.replace(tzinfo=timezone.utc).isoformat() if value and value.tzinfo is None else value.isoformat() if value else None
