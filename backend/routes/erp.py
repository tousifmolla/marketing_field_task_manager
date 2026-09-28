from datetime import date
from decimal import Decimal
from uuid import uuid4
from flask import Blueprint
from extensions import db
from middleware.auth import current_user, roles_required
from models import Order, OrderItem, Product
from services.activity_service import audit
from services.field_validation import FIELD_ROLES, validated, payload, executive, client, identifier
from utils.responses import error, success

bp = Blueprint("erp", __name__, url_prefix="/api/erp")

def dump(row):
    return {"id": row.id, "order_number": row.order_number, "client_id": row.client_id,
            "client": row.client.business_name, "executive_id": row.executive_id,
            "amount": float(row.amount), "status": row.status, "order_date": row.order_date.isoformat(),
            "items": [{"product_id": item.product_id, "product": item.product.product_name,
                       "quantity": item.quantity, "unit_price": float(item.unit_price)} for item in row.items]}

def allowed(user, row):
    return user.role.name in ("ADMIN", "MANAGER") or bool(user.employee and row.executive_id == user.employee.id)

@bp.get("/products")
@roles_required(*FIELD_ROLES)
def products():
    return success([{"id": row.id, "code": row.product_code, "name": row.product_name,
                     "category": row.category, "price": float(row.price), "status": row.status}
                    for row in Product.query.filter_by(status="Active").all()])

@bp.get("/orders")
@roles_required(*FIELD_ROLES)
def orders():
    user = current_user()
    query = Order.query if user.role.name in ("ADMIN", "MANAGER") else Order.query.filter_by(executive_id=user.employee.id if user.employee else -1)
    return success([dump(row) for row in query.order_by(Order.order_date.desc(), Order.id.desc()).all()])

@bp.get("/orders/<int:row_id>")
@roles_required(*FIELD_ROLES)
def detail(row_id):
    row = db.get_or_404(Order, row_id)
    return success(dump(row)) if allowed(current_user(), row) else error("You cannot access this order", 403)

@bp.post("/orders")
@roles_required(*FIELD_ROLES)
@validated
def create():
    user = current_user()
    p = payload(("client_id", "executive_id", "items", "status"))
    if user.role.name in ("ADMIN", "MANAGER"):
        target = executive(p.get("executive_id"))
    else:
        if not user.employee:
            return error("An executive profile is required", 403)
        target = user.employee
        if "executive_id" in p and p["executive_id"] != target.id:
            return error("You can create orders only for yourself", 403)
    customer = client(p.get("client_id"))
    # The existing client catalogue is shared; orders and payroll remain private.
    if p.get("status", "Draft") != "Draft":
        raise ValueError("New orders must start as Draft")
    items = p.get("items")
    if not isinstance(items, list) or not 1 <= len(items) <= 100:
        raise ValueError("Choose between 1 and 100 order items")
    row = Order(order_number=f"ORD-{uuid4().hex[:24]}", client_id=customer.id,
                executive_id=target.id, order_date=date.today(), status="Draft")
    total, seen = Decimal(0), set()
    for item in items:
        if not isinstance(item, dict) or set(item) != {"product_id", "quantity"}:
            raise ValueError("Each item requires a product and quantity; prices are set by the server")
        product_id = identifier(item.get("product_id"), "product")
        product = db.session.get(Product, product_id)
        quantity = item.get("quantity")
        if not product or product.status != "Active" or type(quantity) is not int or not 1 <= quantity <= 10000 or product_id in seen:
            raise ValueError("Choose active products once each with quantities between 1 and 10000")
        seen.add(product_id)
        row.items.append(OrderItem(product_id=product.id, quantity=quantity, unit_price=product.price))
        total += product.price * quantity
    if total > Decimal("9999999999.99"):
        raise ValueError("Order total exceeds the supported amount")
    row.amount = total
    db.session.add(row)
    db.session.flush()
    audit(user.id, "ORDER_CREATE", "order", row.id, row.order_number)
    db.session.commit()
    return success(dump(row), "Order created", 201)

@bp.patch("/orders/<int:row_id>")
@roles_required("ADMIN", "MANAGER")
@validated
def update(row_id):
    row = db.get_or_404(Order, row_id)
    p = payload(("status",))
    status = p.get("status")
    if status not in ("Confirmed", "Cancelled"):
        raise ValueError("Select Confirmed or Cancelled")
    if row.status != "Draft":
        return error("Only draft orders can be confirmed or cancelled", 409)
    changed = Order.query.filter_by(id=row.id, status="Draft").update({"status": status}, synchronize_session=False)
    if changed != 1:
        db.session.rollback()
        return error("Order changed. Refresh and retry.", 409)
    audit(current_user().id, "ORDER_STATUS", "order", row.id, status)
    db.session.commit()
    return success(dump(row), "Order status saved")
