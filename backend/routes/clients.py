import re
from datetime import datetime
from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from extensions import db
from middleware.auth import current_user, roles_required
from models import Client, ClientVisit, EmployeeLocation
from services.activity_service import audit, record_activity
from utils.responses import error, success

bp=Blueprint("clients",__name__,url_prefix="/api")
def dump(c):
    from models import Photo
    photos = Photo.query.filter_by(client_id=c.id).all()
    return {"id": c.id, "client_code": c.client_code, "business_name": c.business_name,
            "contact_person": c.contact_person, "mobile": c.mobile, "address": c.address,
            "city": c.city, "state": c.state, "pin_code": c.pin_code, "latitude": c.latitude,
            "longitude": c.longitude, "business_type": c.business_type,
            "interested_product": c.interested_product, "created_by": c.created_by,
            "photos": [{"id": p.id, "url": f"/photos/{p.id}/file"} for p in photos]}
def validate(p):
    missing=[x for x in ("business_name","contact_person","mobile","address") if not p.get(x)]
    if missing:return f"Required fields: {', '.join(missing)}"
    if not re.fullmatch(r"[6-9]\d{9}",str(p["mobile"])):return "Enter a valid 10-digit Indian mobile number"
    if p.get("pin_code") and not re.fullmatch(r"\d{6}",str(p["pin_code"])):return "PIN code must contain 6 digits"
def assign(c,p):
    for k in ("business_name","contact_person","mobile","alternate_mobile","email","address","city","district","state","pin_code","latitude","longitude","business_type","gst_number","interested_product","expected_order_value","remarks"):
        if k in p:setattr(c,k,p[k])
@bp.post("/clients")
@roles_required("ADMIN", "MANAGER", "MARKETING_EXECUTIVE")
def create():
    user=current_user(); p=request.get_json(silent=True) or {}; problem=validate(p)
    if problem:return error(problem,422)
    c=Client(client_code=f"CLI-{datetime.now():%Y%m%d%H%M%S%f}"[:24],created_by=user.id,business_name="",contact_person="",mobile="",address=""); assign(c,p); db.session.add(c); db.session.flush()
    if user.employee:
        record_activity(user.employee.id,"CLIENT_ONBOARDED",f"Onboarded {c.business_name}",client_id=c.id)
        if c.latitude is not None and c.longitude is not None:db.session.add(EmployeeLocation(employee_id=user.employee.id,latitude=c.latitude,longitude=c.longitude,activity_type="client_onboarding"))
    audit(user.id,"CLIENT_CREATE","client",c.id,c.business_name); db.session.commit(); return success(dump(c),"Client created",201)
@bp.get("/clients")
@jwt_required()
def clients(): return success([dump(c) for c in Client.query.order_by(Client.created_at.desc()).all()])
@bp.get("/clients/<int:client_id>")
@jwt_required()
def get_client(client_id): return success(dump(Client.query.get_or_404(client_id)))
@bp.put("/clients/<int:client_id>")
@roles_required("ADMIN", "MANAGER", "MARKETING_EXECUTIVE")
def edit(client_id):
    c=db.get_or_404(Client, client_id)
    user = current_user()
    if user.role.name not in ("ADMIN", "MANAGER") and c.created_by != user.id: return error("You cannot edit this client", 403)
    p=request.get_json(silent=True) or {}; merged={"business_name":p.get("business_name",c.business_name),"contact_person":p.get("contact_person",c.contact_person),"mobile":p.get("mobile",c.mobile),"address":p.get("address",c.address),"pin_code":p.get("pin_code",c.pin_code)}; problem=validate(merged)
    if problem:return error(problem,422)
    assign(c,p); audit(current_user().id,"CLIENT_UPDATE","client",c.id); db.session.commit(); return success(dump(c),"Client updated")
@bp.post("/client-visits")
@roles_required("ADMIN", "MANAGER", "MARKETING_EXECUTIVE")
def visit():
    user=current_user(); p=request.get_json(silent=True) or {}
    if not user.employee:return error("No employee profile",400)
    row=ClientVisit(client_id=p.get("client_id"),employee_id=user.employee.id,purpose=p.get("purpose"),notes=p.get("notes"),result=p.get("result"),status=p.get("status","Visited"),latitude=p.get("latitude"),longitude=p.get("longitude"),follow_up_required=bool(p.get("follow_up_required")))
    db.session.add(row); db.session.flush(); record_activity(user.employee.id,"CLIENT_VISIT",f"Client visit: {row.status}",client_id=row.client_id); db.session.commit(); return success({"id":row.id,"status":row.status},"Visit recorded",201)
@bp.get("/client-visits/me")
@jwt_required()
def visits():
    user=current_user(); rows=ClientVisit.query.filter_by(employee_id=user.employee.id).order_by(ClientVisit.visit_at.desc()).all() if user.employee else []; return success([{"id":x.id,"client":x.client.business_name,"visit_at":x.visit_at.isoformat(),"status":x.status,"purpose":x.purpose} for x in rows])

@bp.post("/clients/onboard")
@roles_required("ADMIN", "MANAGER", "MARKETING_EXECUTIVE")
def onboard():
    import hashlib
    import json
    import math
    from sqlalchemy.exc import IntegrityError
    from werkzeug.utils import secure_filename
    from models import ClientOnboardingRequest, Photo
    from services.photo_storage import prepare_photo, save_photo, remove_photo

    user = current_user()
    if not user.employee:
        return error("No employee profile linked", 400)
    submission = request.form.get("submission_id", "")
    if not re.fullmatch(r"[a-f0-9]{32}", submission):
        return error("Invalid submission identifier", 422)
    p = {key: request.form.get(key, "").strip() for key in ("business_name", "contact_person", "mobile", "address", "pin_code")}
    problem = validate(p)
    if problem or not re.fullmatch(r"[1-9]\d{5}", p["pin_code"]):
        return error(problem or "Enter a valid 6-digit PIN", 422)
    if any(len(p[key]) > limit for key, limit in (("business_name", 160), ("contact_person", 120), ("address", 1000))):
        return error("Client details are too long", 422)
    try:
        lat, lng, accuracy = (float(request.form.get(key, "")) for key in ("latitude", "longitude", "accuracy"))
        if not all(math.isfinite(v) for v in (lat, lng, accuracy)) or not -90 <= lat <= 90 or not -180 <= lng <= 180 or accuracy < 0:
            raise ValueError()
    except (ValueError, TypeError):
        return error("Valid GPS coordinates and accuracy are required", 422)
    p.update(latitude=lat, longitude=lng)
    file = request.files.get("photo")
    try:
        image, image_hash = prepare_photo(file)
    except ValueError as exc:
        return error(str(exc), 415)
    key = hashlib.sha256(f"{user.id}:{submission}".encode()).hexdigest()
    fingerprint = hashlib.sha256(json.dumps(dict(p, accuracy=accuracy, image_hash=image_hash), sort_keys=True).encode()).hexdigest()

    def replay(existing):
        if existing.request_hash != fingerprint:
            return error("This submission was already used for different details", 409)
        return success(dump(db.session.get(Client, existing.client_id)), "Client already saved")

    existing = db.session.get(ClientOnboardingRequest, key)
    if existing:
        return replay(existing)
    filename = None
    try:
        filename = save_photo(image)
        c = Client(client_code=f"CLI-{key[:24]}", created_by=user.id, business_name="", contact_person="", mobile="", address="", photo_path=filename)
        assign(c, p)
        db.session.add(c)
        db.session.flush()
        photo = Photo(employee_id=user.employee.id, client_id=c.id, file_path=filename,
                      original_name=(secure_filename(file.filename) or "camera.jpg")[:180], latitude=lat, longitude=lng,
                      remarks="Client onboarding camera photo")
        db.session.add(photo)
        db.session.add(ClientOnboardingRequest(id=key, user_id=user.id, client_id=c.id, request_hash=fingerprint))
        db.session.add(EmployeeLocation(employee_id=user.employee.id, latitude=lat, longitude=lng, accuracy=accuracy, activity_type="client_onboarding"))
        record_activity(user.employee.id, "CLIENT_ONBOARDED", f"Onboarded {c.business_name}", client_id=c.id)
        audit(user.id, "CLIENT_CREATE", "client", c.id, c.business_name)
        db.session.commit()
        return success(dump(c), "Client and photo saved", 201)
    except IntegrityError:
        db.session.rollback()
        if filename:
            remove_photo(filename)
        existing = db.session.get(ClientOnboardingRequest, key)
        if existing:
            return replay(existing)
        return error("Client could not be saved. Please retry", 409)
    except Exception:
        db.session.rollback()
        if filename:
            remove_photo(filename)
        raise

