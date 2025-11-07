import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (backend/.env)
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / ".env")

def env_bool(name: str, default: bool = False) -> bool:
    return str(os.getenv(name, str(default))).strip().lower() in {"1", "true", "yes", "y", "on"}

# --- Core ---
SECRET_KEY = os.getenv("SECRET_KEY", "dev-insecure-secret-key-change-me")
DEBUG = env_bool("DEBUG", True)

_raw_hosts = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
ALLOWED_HOSTS = [h.strip() for h in _raw_hosts if h.strip()] or ["*"]

TIME_ZONE = os.getenv("TIME_ZONE", "Asia/Kolkata")
USE_TZ = True

# --- Applications ---
INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "rest_framework",
    "corsheaders",

    # Local apps (you will create these)
    "apps.candidates.apps.CandidatesConfig",
    "apps.documents",
    "apps.agent",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # keep first for CORS
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # optional
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --- Database (SQLite for personal project) ---
# You can ignore DATABASE_URL; defaults to sqlite file in project root.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR.parent / "db.sqlite3",
    }
}

# --- Static & Media (local) ---
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR.parent / "staticfiles"   # collectstatic target (optional)

MEDIA_URL = os.getenv("MEDIA_URL", "/media/")
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", BASE_DIR.parent / "media")).resolve()

# --- File upload caps (best-effort) ---
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "10"))
FILE_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_MB * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_MB * 1024 * 1024

# --- CORS (relaxed for local dev) ---
CORS_ALLOW_ALL_ORIGINS = env_bool("CORS_ALLOW_ALL_ORIGINS", True)

# --- Email / SMS stubs ---
_email_backend_env = os.getenv("EMAIL_BACKEND", "console").strip().lower()
if _email_backend_env == "smtp":
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"  # prints to terminal

DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "Dev <dev@localhost>")
SMS_PROVIDER = os.getenv("SMS_PROVIDER", "console")  # used by your agent stubs

# --- LLM toggle (optional) ---
USE_LLM = env_bool("USE_LLM", False)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# --- DRF defaults (open for personal project) ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
}

# --- Misc ---
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
APPEND_SLASH = True

# Quiet naive host header warnings in DEBUG
if DEBUG and "*" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS += ["*"]
