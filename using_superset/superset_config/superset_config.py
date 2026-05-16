import os

SECRET_KEY = os.environ.get('SUPERSET_SECRET_KEY', 'your-secret-key')
SQLALCHEMY_DATABASE_URI = 'sqlite:////app/superset_home/superset.db'


FEATURE_FLAGS = {
    "EMBEDDED_SUPERSET": True,
}

ENABLE_CORS = True

TALISMAN_ENABLED = False

TALISMAN_CONFIG = {
    "content_security_policy": None,
    "frame_options": None,
}

HTTP_HEADERS = {
    "X-Frame-Options": "ALLOWALL"
}

PUBLIC_ROLE_LIKE = "Admin"

# TẮT CSRF để local demo
WTF_CSRF_ENABLED = False

# COOKIE
SESSION_COOKIE_SAMESITE = None
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = False