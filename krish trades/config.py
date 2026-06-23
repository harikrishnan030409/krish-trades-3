import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # ------------------------------------------------------------------ #
    # Security — set SECRET_KEY in your .env / environment, never hardcode
    # ------------------------------------------------------------------ #
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-before-deploying")

    # ------------------------------------------------------------------ #
    # Database
    # ------------------------------------------------------------------ #
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(basedir, "shop.db"),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ------------------------------------------------------------------ #
    # File uploads
    # ------------------------------------------------------------------ #
    UPLOAD_FOLDER = os.path.join(basedir, "static", "uploads")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

    # ------------------------------------------------------------------ #
    # Admin credentials — override via environment variables in production
    # ------------------------------------------------------------------ #
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

    # ------------------------------------------------------------------ #
    # Store / business settings
    # ------------------------------------------------------------------ #
    STORE_NAME = os.environ.get("STORE_NAME", "KRISH TRADES")
    CURRENCY_SYMBOL = os.environ.get("CURRENCY_SYMBOL", "₹")
