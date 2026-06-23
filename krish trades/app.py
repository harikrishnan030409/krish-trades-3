import os
import uuid
import json
import hmac
import hashlib
from datetime import datetime
from functools import wraps
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify
)
from werkzeug.utils import secure_filename

from config import Config
from models import db, Product, Order, OrderItem, Coupon

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

# Razorpay config — set these in env or config
RAZORPAY_KEY_ID     = os.environ.get("RAZORPAY_KEY_ID", "rzp_test_YOUR_KEY_ID")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "YOUR_KEY_SECRET")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def allowed_file(filename):
    return "." in filename and \
        filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("is_admin"):
            flash("Please log in to access the admin dashboard.", "warning")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated


def get_cart():
    return session.setdefault("cart", {})


def cart_details():
    cart = get_cart()
    items = []
    total = 0.0
    for product_id_str, qty in cart.items():
        product = Product.query.get(int(product_id_str))
        if not product:
            continue
        subtotal = product.final_price * qty
        total += subtotal
        items.append({"product": product, "quantity": qty, "subtotal": subtotal})
    return items, total


def get_applied_coupon(cart_total):
    code = session.get("coupon_code")
    if not code:
        return None, 0.0, None
    coupon = Coupon.query.filter_by(code=code).first()
    if not coupon:
        session.pop("coupon_code", None)
        return None, 0.0, None
    valid, message = coupon.is_valid_for_amount(cart_total)
    if not valid:
        session.pop("coupon_code", None)
        return None, 0.0, message
    discount = min(coupon.discount_amount, cart_total)
    return coupon, discount, None


def generate_order_number():
    return "ORD-" + uuid.uuid4().hex[:8].upper()


# ---------------------------------------------------------------------------
# Storefront Routes
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    featured_products = Product.query.order_by(Product.created_at.desc()).limit(8).all()
    bakrid_products = Product.query.filter_by(is_bakrid_offer=True).order_by(Product.created_at.desc()).limit(8).all()
    categories = db.session.query(Product.category).distinct().all()
    categories = [c[0] for c in categories if c[0]]
    return render_template("home.html", featured_products=featured_products,
                           bakrid_products=bakrid_products, categories=categories)


@app.route("/shop")
def shop():
    category = request.args.get("category")
    search = request.args.get("q", "").strip()
    bakrid_only = request.args.get("bakrid") == "1"

    query = Product.query
    if category:
        query = query.filter_by(category=category)
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
    if bakrid_only:
        query = query.filter_by(is_bakrid_offer=True)

    all_products = query.order_by(Product.created_at.desc()).all()
    categories = db.session.query(Product.category).distinct().all()
    categories = [c[0] for c in categories if c[0]]

    return render_template(
        "shop.html", products=all_products, categories=categories,
        selected_category=category, search_query=search, bakrid_only=bakrid_only
    )


@app.route("/product/<int:product_id>")
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    related = Product.query.filter(
        Product.category == product.category, Product.id != product.id
    ).limit(4).all()
    return render_template("product_detail.html", product=product, related=related)


# ---------------------------------------------------------------------------
# Cart Routes
# ---------------------------------------------------------------------------

@app.route("/cart/add/<int:product_id>", methods=["POST"])
def cart_add(product_id):
    product = Product.query.get_or_404(product_id)
    qty = int(request.form.get("quantity", 1))
    qty = max(1, qty)
    cart = get_cart()
    key = str(product_id)
    cart[key] = cart.get(key, 0) + qty
    session.modified = True
    flash(f"Added {product.name} to your cart.", "success")
    return redirect(request.referrer or url_for("shop"))


@app.route("/cart")
def cart_view():
    items, total = cart_details()
    coupon, discount, coupon_message = get_applied_coupon(total)
    if coupon_message:
        flash(coupon_message, "warning")
    grand_total = total - discount
    return render_template(
        "cart.html", items=items, total=total,
        coupon=coupon, discount=discount, grand_total=grand_total
    )


@app.route("/cart/apply-coupon", methods=["POST"])
def cart_apply_coupon():
    items, total = cart_details()
    code = request.form.get("coupon_code", "").strip().upper()
    if not items:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("cart_view"))
    if not code:
        flash("Please enter a coupon code.", "warning")
        return redirect(url_for("cart_view"))
    coupon = Coupon.query.filter_by(code=code).first()
    if not coupon:
        flash("Invalid coupon code.", "danger")
        return redirect(url_for("cart_view"))
    valid, message = coupon.is_valid_for_amount(total)
    if not valid:
        flash(message, "danger")
        return redirect(url_for("cart_view"))
    session["coupon_code"] = coupon.code
    session.modified = True
    flash(f'Coupon "{coupon.code}" applied! You saved ₹{min(coupon.discount_amount, total):.2f}.', "success")
    return redirect(url_for("cart_view"))


@app.route("/cart/remove-coupon", methods=["POST"])
def cart_remove_coupon():
    session.pop("coupon_code", None)
    session.modified = True
    flash("Coupon removed.", "info")
    return redirect(url_for("cart_view"))


@app.route("/cart/update/<int:product_id>", methods=["POST"])
def cart_update(product_id):
    qty = int(request.form.get("quantity", 1))
    cart = get_cart()
    key = str(product_id)
    if qty <= 0:
        cart.pop(key, None)
    else:
        cart[key] = qty
    session.modified = True
    return redirect(url_for("cart_view"))


@app.route("/cart/remove/<int:product_id>", methods=["POST"])
def cart_remove(product_id):
    cart = get_cart()
    cart.pop(str(product_id), None)
    session.modified = True
    flash("Item removed from cart.", "info")
    return redirect(url_for("cart_view"))


# ---------------------------------------------------------------------------
# Checkout — supports both Cash on Delivery and Online Payment (Razorpay)
# ---------------------------------------------------------------------------

@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    items, total = cart_details()
    if not items:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("shop"))

    coupon, discount, coupon_message = get_applied_coupon(total)
    if coupon_message:
        flash(coupon_message, "warning")
    grand_total = total - discount

    if request.method == "POST":
        name         = request.form.get("name", "").strip()
        email        = request.form.get("email", "").strip()
        phone        = request.form.get("phone", "").strip()
        address_line = request.form.get("address_line", "").strip()
        city         = request.form.get("city", "").strip()
        state        = request.form.get("state", "").strip()
        pincode      = request.form.get("pincode", "").strip()
        notes        = request.form.get("notes", "").strip()
        payment_method = request.form.get("payment_method", "cod")

        if not name or not phone or not address_line or not city or not state or not pincode:
            flash("Please fill in all required fields.", "danger")
            return render_template(
                "checkout.html", items=items, total=total,
                coupon=coupon, discount=discount, grand_total=grand_total,
                razorpay_key=RAZORPAY_KEY_ID
            )

        for item in items:
            if item["quantity"] > item["product"].stock:
                flash(
                    f"Sorry, only {item['product'].stock} unit(s) of "
                    f'"{item["product"].name}" left in stock.',
                    "danger"
                )
                return redirect(url_for("cart_view"))

        coupon, discount, _ = get_applied_coupon(total)
        grand_total = total - discount

        # Store address in session so payment callback can create the order
        session["pending_order"] = {
            "name": name, "email": email, "phone": phone,
            "address_line": address_line, "city": city,
            "state": state, "pincode": pincode, "notes": notes,
            "payment_method": payment_method
        }
        session.modified = True

        if payment_method == "online":
            # Create a Razorpay order via their REST API
            import urllib.request, base64
            amount_paise = int(grand_total * 100)
            rz_payload = json.dumps({
                "amount": amount_paise,
                "currency": "INR",
                "receipt": generate_order_number(),
                "notes": {"customer": name}
            }).encode()
            credentials = base64.b64encode(
                f"{RAZORPAY_KEY_ID}:{RAZORPAY_KEY_SECRET}".encode()
            ).decode()
            rz_req = urllib.request.Request(
                "https://api.razorpay.com/v1/orders",
                data=rz_payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Basic {credentials}"
                }
            )
            try:
                with urllib.request.urlopen(rz_req) as resp:
                    rz_order = json.loads(resp.read())
                session["razorpay_order_id"] = rz_order["id"]
                session.modified = True
                return render_template(
                    "payment.html",
                    rz_order=rz_order,
                    razorpay_key=RAZORPAY_KEY_ID,
                    grand_total=grand_total,
                    name=name, email=email, phone=phone
                )
            except Exception as e:
                flash(f"Payment gateway error: {e}. Please try Cash on Delivery.", "danger")
                # Fall through to COD
                payment_method = "cod"

        # ---- Cash on Delivery ----
        order = Order(
            order_number=generate_order_number(),
            customer_name=name, email=email, phone=phone,
            address_line=address_line, city=city, state=state, pincode=pincode,
            notes=notes, subtotal_amount=total,
            coupon_code=coupon.code if coupon else None,
            coupon_discount=discount,
            total_amount=grand_total, status="Pending",
            payment_method="Cash on Delivery"
        )
        db.session.add(order)
        db.session.flush()
        for item in items:
            product = item["product"]
            db.session.add(OrderItem(
                order_id=order.id, product_id=product.id,
                product_name=product.name, unit_price=product.final_price,
                quantity=item["quantity"]
            ))
            product.stock = max(0, product.stock - item["quantity"])
        if coupon:
            coupon.times_used += 1
        db.session.commit()
        session["cart"] = {}
        session.pop("coupon_code", None)
        session.pop("pending_order", None)
        session.modified = True
        return redirect(url_for("order_confirmation", order_number=order.order_number))

    return render_template(
        "checkout.html", items=items, total=total,
        coupon=coupon, discount=discount, grand_total=grand_total,
        razorpay_key=RAZORPAY_KEY_ID
    )


@app.route("/payment/verify", methods=["POST"])
def payment_verify():
    """Razorpay calls back here after the user completes payment in the widget."""
    data = request.form
    rz_order_id   = data.get("razorpay_order_id", "")
    rz_payment_id = data.get("razorpay_payment_id", "")
    rz_signature  = data.get("razorpay_signature", "")

    expected = hmac.new(
        RAZORPAY_KEY_SECRET.encode(),
        f"{rz_order_id}|{rz_payment_id}".encode(),
        hashlib.sha256
    ).hexdigest()

    pending = session.get("pending_order", {})
    items, total = cart_details()
    coupon, discount, _ = get_applied_coupon(total)
    grand_total = total - discount

    if hmac.compare_digest(expected, rz_signature):
        order = Order(
            order_number=generate_order_number(),
            customer_name=pending.get("name", ""),
            email=pending.get("email", ""),
            phone=pending.get("phone", ""),
            address_line=pending.get("address_line", ""),
            city=pending.get("city", ""),
            state=pending.get("state", ""),
            pincode=pending.get("pincode", ""),
            notes=pending.get("notes", ""),
            subtotal_amount=total,
            coupon_code=coupon.code if coupon else None,
            coupon_discount=discount,
            total_amount=grand_total,
            status="Confirmed",
            payment_method=f"Online (Razorpay: {rz_payment_id})"
        )
        db.session.add(order)
        db.session.flush()
        for item in items:
            product = item["product"]
            db.session.add(OrderItem(
                order_id=order.id, product_id=product.id,
                product_name=product.name, unit_price=product.final_price,
                quantity=item["quantity"]
            ))
            product.stock = max(0, product.stock - item["quantity"])
        if coupon:
            coupon.times_used += 1
        db.session.commit()
        session["cart"] = {}
        session.pop("coupon_code", None)
        session.pop("pending_order", None)
        session.pop("razorpay_order_id", None)
        session.modified = True
        flash("Payment successful! Your order has been confirmed.", "success")
        return redirect(url_for("order_confirmation", order_number=order.order_number))
    else:
        flash("Payment verification failed. Please contact support.", "danger")
        return redirect(url_for("cart_view"))


@app.route("/order-confirmation/<order_number>")
def order_confirmation(order_number):
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    return render_template("order_confirmation.html", order=order)


# ---------------------------------------------------------------------------
# Admin Routes
# ---------------------------------------------------------------------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == app.config["ADMIN_USERNAME"] and password == app.config["ADMIN_PASSWORD"]:
            session["is_admin"] = True
            flash("Welcome back, Admin!", "success")
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid username or password.", "danger")
    return render_template("admin/login.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("admin_login"))


@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    stats = {
        "product_count": Product.query.count(),
        "order_count": Order.query.count(),
        "pending_count": Order.query.filter_by(status="Pending").count(),
        "revenue": db.session.query(db.func.sum(Order.total_amount))
            .filter(Order.status != "Cancelled").scalar() or 0,
    }
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    return render_template("admin/dashboard.html", stats=stats, recent_orders=recent_orders)


@app.route("/admin/products")
@login_required
def admin_products():
    all_products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template("admin/manage_products.html", products=all_products)


@app.route("/admin/products/add", methods=["GET", "POST"])
@login_required
def admin_add_product():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        price = request.form.get("price", "0") or 0
        stock = request.form.get("stock", "0") or 0
        discount_percent = request.form.get("discount_percent", "0") or 0
        is_bakrid_offer = bool(request.form.get("is_bakrid_offer"))
        image_filename = None
        file = request.files.get("image")
        if file and file.filename and allowed_file(file.filename):
            image_filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], image_filename))
        new_product = Product(
            name=name, category=category, description=description,
            price=float(price), stock=int(stock), image=image_filename,
            discount_percent=float(discount_percent), is_bakrid_offer=is_bakrid_offer
        )
        db.session.add(new_product)
        db.session.commit()
        flash("Product added successfully.", "success")
        return redirect(url_for("admin_products"))
    return render_template("admin/product_form.html", product=None)


@app.route("/admin/products/edit/<int:product_id>", methods=["GET", "POST"])
@login_required
def admin_edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    if request.method == "POST":
        product.name = request.form.get("name", "").strip()
        product.category = request.form.get("category", "").strip()
        product.description = request.form.get("description", "").strip()
        product.price = float(request.form.get("price", "0") or 0)
        product.stock = int(request.form.get("stock", "0") or 0)
        product.discount_percent = float(request.form.get("discount_percent", "0") or 0)
        product.is_bakrid_offer = bool(request.form.get("is_bakrid_offer"))
        file = request.files.get("image")
        if file and file.filename and allowed_file(file.filename):
            image_filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], image_filename))
            product.image = image_filename
        db.session.commit()
        flash("Product updated successfully.", "success")
        return redirect(url_for("admin_products"))
    return render_template("admin/product_form.html", product=product)


@app.route("/admin/products/delete/<int:product_id>", methods=["POST"])
@login_required
def admin_delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash("Product deleted.", "info")
    return redirect(url_for("admin_products"))


@app.route("/admin/orders")
@login_required
def admin_orders():
    status_filter = request.args.get("status")
    query = Order.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    orders = query.order_by(Order.created_at.desc()).all()
    return render_template("admin/manage_orders.html", orders=orders, status_filter=status_filter)


@app.route("/admin/orders/<int:order_id>")
@login_required
def admin_order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template("admin/order_detail.html", order=order)


@app.route("/admin/orders/<int:order_id>/status", methods=["POST"])
@login_required
def admin_update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get("status")
    valid_statuses = {"Pending", "Confirmed", "Shipped", "Delivered", "Cancelled"}
    if new_status in valid_statuses:
        order.status = new_status
        db.session.commit()
        flash(f"Order {order.order_number} marked as {new_status}.", "success")
    return redirect(url_for("admin_order_detail", order_id=order.id))


@app.route("/admin/coupons")
@login_required
def admin_coupons():
    all_coupons = Coupon.query.order_by(Coupon.created_at.desc()).all()
    return render_template("admin/manage_coupons.html", coupons=all_coupons)


@app.route("/admin/coupons/add", methods=["GET", "POST"])
@login_required
def admin_add_coupon():
    if request.method == "POST":
        code = request.form.get("code", "").strip().upper()
        discount_amount = request.form.get("discount_amount", "0") or 0
        min_order_amount = request.form.get("min_order_amount", "0") or 0
        expiry_date_str = request.form.get("expiry_date", "").strip()
        is_active = bool(request.form.get("is_active"))
        if not code:
            flash("Coupon code is required.", "danger")
            return render_template("admin/coupon_form.html", coupon=None)
        if Coupon.query.filter_by(code=code).first():
            flash(f'A coupon with code "{code}" already exists.', "danger")
            return render_template("admin/coupon_form.html", coupon=None)
        expiry_date = None
        if expiry_date_str:
            expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d").date()
        new_coupon = Coupon(
            code=code, discount_amount=float(discount_amount),
            min_order_amount=float(min_order_amount),
            expiry_date=expiry_date, is_active=is_active
        )
        db.session.add(new_coupon)
        db.session.commit()
        flash("Coupon created successfully.", "success")
        return redirect(url_for("admin_coupons"))
    return render_template("admin/coupon_form.html", coupon=None)


@app.route("/admin/coupons/edit/<int:coupon_id>", methods=["GET", "POST"])
@login_required
def admin_edit_coupon(coupon_id):
    coupon = Coupon.query.get_or_404(coupon_id)
    if request.method == "POST":
        code = request.form.get("code", "").strip().upper()
        if not code:
            flash("Coupon code is required.", "danger")
            return render_template("admin/coupon_form.html", coupon=coupon)
        existing = Coupon.query.filter_by(code=code).first()
        if existing and existing.id != coupon.id:
            flash(f'A coupon with code "{code}" already exists.', "danger")
            return render_template("admin/coupon_form.html", coupon=coupon)
        expiry_date_str = request.form.get("expiry_date", "").strip()
        coupon.code = code
        coupon.discount_amount = float(request.form.get("discount_amount", "0") or 0)
        coupon.min_order_amount = float(request.form.get("min_order_amount", "0") or 0)
        coupon.expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d").date() if expiry_date_str else None
        coupon.is_active = bool(request.form.get("is_active"))
        db.session.commit()
        flash("Coupon updated successfully.", "success")
        return redirect(url_for("admin_coupons"))
    return render_template("admin/coupon_form.html", coupon=coupon)


@app.route("/admin/coupons/delete/<int:coupon_id>", methods=["POST"])
@login_required
def admin_delete_coupon(coupon_id):
    coupon = Coupon.query.get_or_404(coupon_id)
    db.session.delete(coupon)
    db.session.commit()
    flash("Coupon deleted.", "info")
    return redirect(url_for("admin_coupons"))


# ---------------------------------------------------------------------------
# Database initialization with expanded sample data
# ---------------------------------------------------------------------------

def init_db_with_sample_data():
    db.create_all()

    if Product.query.count() == 0:
        sample_products = [
            # Electronics
            Product(name="Wireless Earbuds Pro", category="Electronics",
                    description="Bluetooth 5.3 earbuds with active noise cancellation, 30hr battery life, and IPX5 water resistance. Perfect for workouts and commutes.",
                    price=1499.00, stock=25, image="wireless-earbuds.png",
                    discount_percent=15, is_bakrid_offer=True),
            Product(name="Smart Fitness Watch", category="Electronics",
                    description="1.4\" AMOLED touchscreen smartwatch with heart-rate, SpO2, sleep tracking, and 7-day battery. Compatible with Android & iOS.",
                    price=2499.00, stock=15, image=None,
                    discount_percent=20, is_bakrid_offer=True),
            Product(name="LED Desk Lamp", category="Electronics",
                    description="Adjustable 5-level brightness, USB-C rechargeable, eye-care lighting with warm/cool/natural modes. Foldable for travel.",
                    price=1199.00, stock=20, image="desk-lamp.png"),
            Product(name="Portable Power Bank 20000mAh", category="Electronics",
                    description="Dual USB + Type-C 20W fast charging power bank. Powers a smartphone 5× over. LED indicator, airline-safe.",
                    price=1799.00, stock=30, image=None, discount_percent=10),
            Product(name="Mechanical Keyboard TKL", category="Electronics",
                    description="Tenkeyless mechanical keyboard with blue switches, RGB backlight, and detachable USB-C cable. For gamers and typists.",
                    price=3499.00, stock=10, image=None, discount_percent=15),
            Product(name="USB-C Hub 7-in-1", category="Electronics",
                    description="7-in-1 hub: 4K HDMI, 3× USB 3.0, SD/TF card reader, 100W PD charging. Compatible with MacBook and laptops.",
                    price=1299.00, stock=18, image=None),

            # Clothing
            Product(name="Cotton T-Shirt", category="Clothing",
                    description="100% ring-spun cotton, pre-shrunk, breathable. Available in 12 colours, sizes S–3XL.",
                    price=499.00, stock=50, image="cotton-tshirt.png",
                    discount_percent=10),
            Product(name="Men's Kurta Pajama Set", category="Clothing",
                    description="Elegant festive kurta pajama in soft cotton. Perfect for Eid, weddings, and special occasions. Sizes M–XXL.",
                    price=1999.00, stock=20, image=None,
                    discount_percent=25, is_bakrid_offer=True),
            Product(name="Women's Anarkali Kurti", category="Clothing",
                    description="Floor-length Anarkali kurti in rayon fabric with intricate block-print. Sizes XS–2XL.",
                    price=1599.00, stock=15, image=None,
                    discount_percent=20, is_bakrid_offer=True),
            Product(name="Unisex Hoodie", category="Clothing",
                    description="280GSM fleece-lined hoodie with kangaroo pocket. Sizes S–XXL in 8 colours. Pre-shrunk and pill-resistant.",
                    price=1299.00, stock=25, image=None, discount_percent=10),
            Product(name="Premium Denim Jeans", category="Clothing",
                    description="Stretch denim with 2% elastane for comfort. Slim-fit cut, 5-pocket design. Waist 28–40.",
                    price=1899.00, stock=20, image=None),

            # Home & Kitchen
            Product(name="Stainless Steel Water Bottle", category="Home & Kitchen",
                    description="1L double-walled insulated bottle, keeps drinks cold 24hr / hot 12hr. BPA-free, leak-proof flip cap.",
                    price=699.00, stock=40, image="water-bottle.png"),
            Product(name="Chrome Insulated Bottle", category="Home & Kitchen",
                    description="Premium mirror-finish insulated bottle. 750ml, keeps drinks ice-cold for 18hrs. Vacuum-sealed lid.",
                    price=999.00, stock=18, image="pexels-mikhail-nilov-7815021.jpg",
                    discount_percent=15),
            Product(name="Cast Iron Kadai 2.5L", category="Home & Kitchen",
                    description="Pre-seasoned cast iron kadai with glass lid. Even heat distribution, suitable for induction and gas stoves.",
                    price=1599.00, stock=12, image=None, discount_percent=10),
            Product(name="Airtight Food Container Set (5pcs)", category="Home & Kitchen",
                    description="Set of 5 BPA-free airtight containers: 250ml, 500ml, 1L, 1.5L, 2L. Dishwasher-safe, stackable.",
                    price=799.00, stock=35, image=None),
            Product(name="Bamboo Cutting Board", category="Home & Kitchen",
                    description="Large 45×30cm bamboo cutting board with juice groove and anti-slip rubber feet. Eco-friendly and knife-friendly.",
                    price=649.00, stock=22, image=None),

            # Fitness
            Product(name="Yoga Mat 6mm", category="Fitness",
                    description="Non-slip 6mm thick yoga mat with alignment lines and carry strap. 183×61cm. Eco-friendly TPE material.",
                    price=899.00, stock=15, image="yoga-mat.png"),
            Product(name="Cork Yoga Blocks (Pair)", category="Fitness",
                    description="Eco-friendly cork yoga blocks for support and stability. 23×15×7.5cm, firm and lightweight.",
                    price=599.00, stock=30, image="samantha-sheppard-b8Q5fHBsyik-unsplash.jpg"),
            Product(name="Resistance Bands Set (5 levels)", category="Fitness",
                    description="Set of 5 resistance bands: 5–40 lbs. Latex-free, carry bag included. For strength training and physio.",
                    price=699.00, stock=28, image=None, discount_percent=10),
            Product(name="Skipping Rope — Speed Pro", category="Fitness",
                    description="Adjustable steel cable speed rope with ball-bearing handles and digital jump counter. Up to 5 metres/sec.",
                    price=449.00, stock=40, image=None),
            Product(name="Foam Roller 60cm", category="Fitness",
                    description="EVA foam roller for muscle recovery, myofascial release, and stretching. High-density, 60cm.",
                    price=799.00, stock=18, image=None),

            # Accessories
            Product(name="Backpack 30L", category="Accessories",
                    description="Water-resistant 30L backpack with padded 15\" laptop compartment, USB charging port, and ergonomic straps.",
                    price=1799.00, stock=12, image="backpack.jpg",
                    discount_percent=10, is_bakrid_offer=True),
            Product(name="Attar Perfume Gift Set", category="Accessories",
                    description="Alcohol-free attar gift set with 3 signature fragrances in 8ml roll-on bottles. Elegant gift packaging.",
                    price=1299.00, stock=22, image=None,
                    discount_percent=30, is_bakrid_offer=True),
            Product(name="Genuine Leather Wallet", category="Accessories",
                    description="Full-grain leather bifold wallet with 8 card slots, RFID-blocking lining, and cash compartment.",
                    price=699.00, stock=28, image=None),
            Product(name="Stainless Steel Watch — Classic", category="Accessories",
                    description="Minimalist stainless steel watch with sapphire glass, 5ATM water resistance, and leather strap. Unisex.",
                    price=2999.00, stock=10, image=None, discount_percent=15, is_bakrid_offer=True),
            Product(name="Sunglasses — UV400 Polarised", category="Accessories",
                    description="TR-90 frame with polarised UV400 lenses. Blocks 100% UVA/UVB. Comes with hard case and cleaning cloth.",
                    price=899.00, stock=20, image=None, discount_percent=10),

            # Grocery
            Product(name="Premium Dates Gift Box", category="Grocery",
                    description="Assorted premium Medjool and Ajwa dates in an elegant magnetic gift box. 500g. Ideal Bakrid/Eid gift.",
                    price=799.00, stock=35, image=None,
                    discount_percent=15, is_bakrid_offer=True),
            Product(name="Dry Fruits Hamper", category="Grocery",
                    description="Generous hamper of California almonds, Kaju cashews, pistachios, and golden raisins. 1kg assorted.",
                    price=1499.00, stock=18, image=None,
                    discount_percent=20, is_bakrid_offer=True),
            Product(name="Cold-Press Coconut Oil 1L", category="Grocery",
                    description="100% pure cold-press virgin coconut oil. Unrefined, chemical-free. For cooking, hair, and skin.",
                    price=549.00, stock=30, image=None),
            Product(name="Organic Turmeric Powder 200g", category="Grocery",
                    description="Single-origin organic turmeric from Tamil Nadu. High curcumin content, stone-ground. No additives.",
                    price=249.00, stock=50, image=None),
        ]
        db.session.bulk_save_objects(sample_products)

    if Coupon.query.count() == 0:
        sample_coupons = [
            Coupon(code="WELCOME100", discount_amount=100.0, min_order_amount=500.0,  is_active=True),
            Coupon(code="BAKRID200",  discount_amount=200.0, min_order_amount=1500.0, is_active=True),
            Coupon(code="FLAT50",     discount_amount=50.0,  min_order_amount=0.0,    is_active=True),
            Coupon(code="ONLINE150",  discount_amount=150.0, min_order_amount=999.0,  is_active=True),
        ]
        db.session.bulk_save_objects(sample_coupons)

    db.session.commit()


@app.cli.command("init-db")
def init_db_command():
    with app.app_context():
        init_db_with_sample_data()
    print("Database initialized with sample data.")


if __name__ == "__main__":
    with app.app_context():
        init_db_with_sample_data()
    port = int(os.environ.get("PORT", 81))
    app.run(host="0.0.0.0", port=port, debug=True)
