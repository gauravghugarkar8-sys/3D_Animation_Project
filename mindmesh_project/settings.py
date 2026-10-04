"""
Django settings for the MindMesh project.

MindMesh is a JARVIS-style personal AI assistant dashboard: a live
conversation panel, an animated knowledge visual, real-time system stats,
weather, and voice I/O — all served by a Django backend with a real LLM
tool-calling agent (see assistant/agent/core_agent.py) that decides for
itself which tools to call (weather, system stats, a matching 3D visual)
rather than a hand-written rule/keyword router.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env explicitly from the project root (same folder as manage.py),
# regardless of the current working directory the server was started
# from. Calling load_dotenv() with no path relies on auto-detection that
# can silently fail to find the file — this doesn't.
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

# --------------------------------------------------------------------------
# Core Django settings
# --------------------------------------------------------------------------

SECRET_KEY = os.environ.get(
    "SECRET_KEY", "dev-insecure-secret-key-change-me-before-deploying"
)

DEBUG = os.environ.get("DEBUG", "True") == "True"

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "assistant.apps.AssistantConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "mindmesh_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "assistant" / "templates"],
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

WSGI_APPLICATION = "mindmesh_project.wsgi.application"
ASGI_APPLICATION = "mindmesh_project.asgi.application"

# --------------------------------------------------------------------------
# Database — SQLite is plenty for a local assistant dashboard.
# --------------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --------------------------------------------------------------------------
# Internationalization
# --------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.environ.get("TIME_ZONE", "Asia/Kolkata")
USE_I18N = True
USE_TZ = True

# --------------------------------------------------------------------------
# Static files
# --------------------------------------------------------------------------

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "assistant" / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --------------------------------------------------------------------------
# MindMesh assistant configuration
# --------------------------------------------------------------------------

ASSISTANT_NAME = os.environ.get("ASSISTANT_NAME", "MindMesh")
WAKE_WORD = os.environ.get("WAKE_WORD", "hey mindmesh")

OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")
DEFAULT_CITY = os.environ.get("DEFAULT_CITY", "Aurangabad,IN")

LLM_API_KEY = os.environ.get("LLM_API_KEY", "AQ.Ab8RN6KwpnZ_8kn2aOi5V3Y-iSmzhWZzI_JEmdS-Li1yBWbG8g")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
LLM_MODEL = os.environ.get("LLM_MODEL", "gemini-3-flash-preview")
# Optional override. Leave unset for auto (1.0 for Gemini 3 models, 0 otherwise).
_temp = os.environ.get("LLM_TEMPERATURE", "").strip()
LLM_TEMPERATURE = float(_temp) if _temp else None
