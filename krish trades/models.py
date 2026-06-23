from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False, default=0.0)
    stock = db.Column(db.Integer, nullable=False, default=0)
    image = db.Column(db.String(255), nullable=True)  # filename in static/uploads
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Discount + festive offer support
    discount_percent = db.Column(db.Float, nullable=False, default=0.0)
    is_bakrid_offer = db.Column(db.Boolean, nullable=False, default=False)

    def in_stock(self):
        return self.stock > 0

    @property
    def has_discount(self):
        return bool(self.discount_percent and self.discount_percent > 0)

    @property
    def final_price(self):
        """Price after discount is applied. Falls back to regular price if no discount."""
        if self.has_discount:
            return round(self.price * (1 - self.discount_percent / 100), 2)
        return self.price

    @property
    def savings(self):
        return round(self.price - self.final_price, 2)

    def __repr__(self):
        return f"<Product {self.name}>"


class Coupon(db.Model):
    __tablename__ = "coupons"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False)

    # Fixed amount off (in ₹)
    discount_amount = db.Column(db.Float, nullable=False, default=0.0)

    # Cart total must be at least this much for the coupon to apply
    min_order_amount = db.Column(db.Float, nullable=False, default=0.0)

    expiry_date = db.Column(db.Date, nullable=True)  # null = never expires
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    # How many times this coupon has been redeemed
    times_used = db.Column(db.Integer, nullable=False, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def is_expired(self):
        if not self.expiry_date:
            return False
        return self.expiry_date < datetime.utcnow().date()

    def is_valid_for_amount(self, cart_total):
        """Check the coupon can be applied to a cart of the given total."""
        if not self.is_active:
            return False, "This coupon is no longer active."
        if self.is_expired:
            return False, "This coupon has expired."
        if cart_total < self.min_order_amount:
            return False, f"Add ₹{self.min_order_amount:.2f} more to use this coupon."
        return True, ""

    def __repr__(self):
        return f"<Coupon {self.code}>"


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True, nullable=False)

    # Guest checkout details
    customer_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=True)
    phone = db.Column(db.String(30), nullable=False)
    address_line = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    pincode = db.Column(db.String(20), nullable=False)
    notes = db.Column(db.Text, nullable=True)

    subtotal_amount = db.Column(db.Float, nullable=False, default=0.0)
    coupon_code = db.Column(db.String(40), nullable=True)
    coupon_discount = db.Column(db.Float, nullable=False, default=0.0)
    total_amount = db.Column(db.Float, nullable=False, default=0.0)

    # Pending -> Confirmed -> Shipped -> Delivered -> Cancelled
    status = db.Column(db.String(20), nullable=False, default="Pending")
    payment_method = db.Column(db.String(50), nullable=False, default="Cash on Delivery")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship("OrderItem", backref="order", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Order {self.order_number}>"


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=True)

    # Snapshot fields so order history stays correct even if product is later edited/deleted
    product_name = db.Column(db.String(150), nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    @property
    def subtotal(self):
        return self.unit_price * self.quantity

    def __repr__(self):
        return f"<OrderItem {self.product_name} x{self.quantity}>"
