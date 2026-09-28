from flask import Blueprint
from flask_jwt_extended import jwt_required
from extensions import db
from middleware.auth import current_user
from models import Notification
from utils.responses import success
bp=Blueprint("notifications",__name__,url_prefix="/api/notifications")
def dump(x):return {"id":x.id,"title":x.title,"message":x.message,"type":x.notification_type,"is_read":x.is_read,"created_at":x.created_at.isoformat()}
@bp.get("")
@jwt_required()
def items():return success([dump(x) for x in Notification.query.filter_by(user_id=current_user().id).order_by(Notification.created_at.desc()).all()])
@bp.patch("/<int:item_id>/read")
@jwt_required()
def read(item_id):
    x=Notification.query.filter_by(id=item_id,user_id=current_user().id).first_or_404(); x.is_read=True; db.session.commit(); return success(dump(x),"Marked as read")
@bp.patch("/read-all")
@jwt_required()
def read_all():Notification.query.filter_by(user_id=current_user().id,is_read=False).update({"is_read":True}); db.session.commit(); return success(message="All notifications marked as read")
