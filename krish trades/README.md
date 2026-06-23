# 🛒 KRISH TRADES — Flask E-Commerce Website

A lightweight, fully functional e-commerce storefront built with Python Flask. Customers can browse products, add items to a cart, and place Cash-on-Delivery orders — no account required. An admin panel handles products, orders, and coupon codes.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-2.x-black?logo=flask)
![SQLite](https://img.shields.io/badge/Database-SQLite-lightgrey?logo=sqlite)
![Bootstrap](https://img.shields.io/badge/UI-Bootstrap%205-purple?logo=bootstrap)

---

## ✨ Features

### Customer-Facing
| # | Page | Description |
|---|------|-------------|
| 1 | Home | Featured products + Bakrid Special Offers banner |
| 2 | Shop | Full catalog with category filter, search, and Bakrid filter |
| 3 | Product Detail | Discounted pricing, savings shown, related products |
| 4 | Cart | Session-based (no login needed), coupon code support |
| 5 | Checkout | Cash on Delivery — collects name, address, phone |
| 6 | Order Confirmation | Order number, summary, coupon savings |

### Admin Panel (`/admin`)
- **Dashboard** — order and revenue overview
- **Product Management** — CRUD with image upload, stock tracking, discount %, Bakrid-offer toggle
- **Order Management** — view orders, update status (Pending → Confirmed → Shipped → Delivered / Cancelled)
- **Coupon Management** — create/edit/delete fixed-amount coupons with optional minimum order and expiry date

---

## 🚀 Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/your-username/shopsite_enhanced.git
cd shopsite_enhanced
```

### 2. Create and activate a virtual environment
```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
```bash
cp .env.example .env
# Edit .env and set SECRET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD, etc.
```

### 5. Run the development server
```bash
python app.py
```

The database (`shop.db`) and 14 sample products are created automatically on first run.

| URL | Description |
|-----|-------------|
| http://127.0.0.1:5000/ | Customer storefront |
| http://127.0.0.1:5000/admin/login | Admin panel |

---

## 🔐 Default Admin Credentials

> ⚠️ **Change these before any public deployment** — set `ADMIN_USERNAME` and `ADMIN_PASSWORD` in your `.env` file.

```
Username: admin
Password: admin123
```

Sample coupon codes seeded on first run: `WELCOME100`, `BAKRID200`, `FLAT50`

---

## ⚙️ Configuration

All settings are in `config.py` and can be overridden via environment variables (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | *(dev placeholder)* | Flask session secret — **must** be changed in production |
| `DATABASE_URL` | `sqlite:///shop.db` | SQLAlchemy database URI |
| `ADMIN_USERNAME` | `admin` | Admin login username |
| `ADMIN_PASSWORD` | `admin123` | Admin login password |
| `STORE_NAME` | `KRISH TRADES` | Displayed in the storefront |
| `CURRENCY_SYMBOL` | `₹` | Currency symbol |
| `RAZORPAY_KEY_ID` | — | Optional: Razorpay key (if enabling online payments) |
| `RAZORPAY_KEY_SECRET` | — | Optional: Razorpay secret |

---

## 🗂️ Project Structure

```
shopsite_enhanced/
├── app.py                  # All routes — storefront, cart, checkout, admin
├── config.py               # App config (reads from environment variables)
├── models.py               # SQLAlchemy models: Product, Order, OrderItem, Coupon
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── .gitignore
├── static/
│   ├── css/style.css
│   ├── js/reveal.js
│   └── uploads/            # Product images (user-generated, not tracked by Git)
└── templates/
    ├── base.html           # Storefront layout (navbar, cart icon, search)
    ├── home.html
    ├── shop.html
    ├── product_detail.html
    ├── cart.html
    ├── checkout.html
    ├── payment.html
    ├── order_confirmation.html
    └── admin/
        ├── base_admin.html
        ├── login.html
        ├── dashboard.html
        ├── manage_products.html
        ├── product_form.html
        ├── manage_orders.html
        ├── order_detail.html
        ├── manage_coupons.html
        └── coupon_form.html
```

---

## 🔄 Upgrading from an Older Version

If you have an existing `shop.db` from a previous version, delete it before running — the schema has changed and the app will recreate it with fresh sample data.

```bash
rm shop.db
python app.py
```

---

## 🛠️ Tech Stack

- **Backend:** Python 3.8+, Flask 2.x
- **Database:** SQLite via Flask-SQLAlchemy
- **Frontend:** HTML5, Bootstrap 5, Bootstrap Icons
- **Cart:** Flask session (no customer account required)
- **Payments:** Cash on Delivery (Razorpay keys wired in but not active by default)

---

## 🗺️ Possible Future Enhancements

- [ ] Email / SMS order notifications
- [ ] Customer order-tracking page (lookup by order number + phone)
- [ ] Multiple product images per product
- [ ] Customer accounts with order history
- [ ] Deployment guide (Railway / Render / PythonAnywhere)

---

## 📄 License

This project is open-source. See [LICENSE](LICENSE) for details.
