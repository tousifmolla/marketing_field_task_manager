from extensions import db
from models import Activity, AuditLog

def record_activity(employee_id, activity_type, description, client_id=None, task_id=None):
    db.session.add(Activity(employee_id=employee_id, activity_type=activity_type, description=description, client_id=client_id, task_id=task_id))

def audit(user_id, action, entity_type=None, entity_id=None, details=None):
    db.session.add(AuditLog(user_id=user_id, action=action, entity_type=entity_type, entity_id=str(entity_id) if entity_id else None, details=details))
