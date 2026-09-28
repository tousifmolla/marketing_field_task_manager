from .auth import bp as auth_bp
from .attendance import bp as attendance_bp
from .location import bp as location_bp
from .clients import bp as clients_bp
from .tasks import bp as tasks_bp
from .appointments import bp as appointments_bp
from .activities import bp as activities_bp
from .photos import bp as photos_bp
from .payroll import bp as payroll_bp
from .erp import bp as erp_bp
from .admin import bp as admin_bp
from .notifications import bp as notifications_bp

BLUEPRINTS=[auth_bp,attendance_bp,location_bp,clients_bp,tasks_bp,appointments_bp,activities_bp,photos_bp,payroll_bp,erp_bp,admin_bp,notifications_bp]
