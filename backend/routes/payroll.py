from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from flask import Blueprint
from sqlalchemy.exc import IntegrityError
from extensions import db
from middleware.auth import current_user, roles_required
from models import Employee, Notification, Payroll
from services.payroll_service import calculate_net_salary
from services.activity_service import audit
from services.field_validation import validated, payload, identifier, iso
from utils.responses import error, success

bp = Blueprint("payroll", __name__, url_prefix="/api/payroll")
ALL_ROLES = ("ADMIN", "MANAGER", "HR_ACCOUNTS", "MARKETING_EXECUTIVE")
MANAGE = ("ADMIN", "HR_ACCOUNTS")
MONEY = ("basic_salary", "overtime", "ta_da", "sales_incentive", "other_incentive", "deductions")
DAYS = ("working_days", "present_days", "leave_days", "absent_days")

def dump(row):
    result = {key: float(getattr(row, key) or 0) for key in MONEY + ("net_salary",)}
    result.update({key: getattr(row, key) for key in DAYS + ("id", "employee_id", "year", "month", "published")})
    result.update(employee=row.employee.name, created_at=iso(row.created_at), updated_at=iso(row.updated_at))
    return result

def integer(value, low, high, name):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"Enter a valid {name} between {low} and {high}")
    return value

def money(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError("Salary amounts must be valid non-negative numbers")
    try:
        number = Decimal(str(value))
        if not number.is_finite() or number < 0 or number > Decimal("9999999999.99"):
            raise InvalidOperation()
        return number.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        raise ValueError("Salary amounts must be valid non-negative numbers") from None

@bp.get("/me")
@roles_required(*ALL_ROLES)
def mine():
    user = current_user()
    rows = Payroll.query.filter_by(employee_id=user.employee.id, published=True).order_by(Payroll.year.desc(), Payroll.month.desc()).all() if user.employee else []
    return success([dump(row) for row in rows])

@bp.get("")
@roles_required(*MANAGE)
def all_payroll():
    return success([dump(row) for row in Payroll.query.order_by(Payroll.year.desc(), Payroll.month.desc(), Payroll.id.desc()).all()])

@bp.get("/employees")
@roles_required(*MANAGE)
def employees():
    return success([{"id": row.id, "name": row.name} for row in Employee.query.filter_by(active=True).order_by(Employee.name).all()])

@bp.get("/<int:row_id>")
@roles_required(*ALL_ROLES)
def detail(row_id):
    row = db.get_or_404(Payroll, row_id)
    user = current_user()
    if user.role.name not in MANAGE and (not user.employee or row.employee_id != user.employee.id or not row.published):
        return error("You cannot access this payroll record", 403)
    return success(dump(row))

def save(row=None):
    p = payload(("employee_id", "year", "month", "published") + MONEY + DAYS)
    if row:
        for key in ("employee_id", "year", "month"):
            if key in p and p[key] != getattr(row, key):
                raise ValueError("Employee and payroll period cannot be changed")
        employee_id, year, month = row.employee_id, row.year, row.month
    else:
        employee_id = identifier(p.get("employee_id"), "employee")
        year = integer(p.get("year"), 2000, 2100, "year")
        month = integer(p.get("month"), 1, 12, "month")
        row = Payroll.query.filter_by(employee_id=employee_id, year=year, month=month).first()
    employee = db.session.get(Employee, employee_id)
    if not employee or not employee.active:
        raise ValueError("Select an active employee")
    creating = row is None
    row = row or Payroll(employee_id=employee_id, year=year, month=month, published=False)
    was_published = bool(row.published)
    values = {key: money(p[key]) if key in p else getattr(row, key) or Decimal(0) for key in MONEY}
    days = {key: integer(p[key], 0, 31, key.replace("_", " ")) if key in p else getattr(row, key) or 0 for key in DAYS}
    if sum(days[key] for key in ("present_days", "leave_days", "absent_days")) > days["working_days"]:
        raise ValueError("Present, leave and absent days cannot exceed working days")
    published = p.get("published", was_published)
    if type(published) is not bool:
        raise ValueError("Published must be true or false")
    total = calculate_net_salary(**{("basic" if key == "basic_salary" else key): value for key, value in values.items()})
    if total < 0 or total > Decimal("9999999999.99"):
        raise ValueError("Net salary must be non-negative and within the supported amount")
    for key, value in dict(values, **days).items():
        setattr(row, key, value)
    row.net_salary, row.published = total, published
    db.session.add(row)
    try:
        db.session.flush()
        audit(current_user().id, "PAYROLL_CREATE" if creating else "PAYROLL_UPDATE", "payroll", row.id, f"{month}/{year}; published={published}")
        if published and not was_published and employee.user:
            db.session.add(Notification(user_id=employee.user.id, title="Payroll published", message=f"Payslip for {month}/{year} is available", notification_type="payroll"))
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error("Payroll changed. Refresh and retry.", 409)
    return success(dump(row), "Payroll saved", 201 if creating else 200)

@bp.post("")
@roles_required(*MANAGE)
@validated
def upsert():
    return save()

@bp.patch("/<int:row_id>")
@roles_required(*MANAGE)
@validated
def update(row_id):
    return save(db.get_or_404(Payroll, row_id))
