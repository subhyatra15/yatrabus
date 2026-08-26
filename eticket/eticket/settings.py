"""
Django settings for eticket project.
"""
from pathlib import Path
import os
from dotenv import load_dotenv
from datetime import timedelta

# Build paths inside the project like this: BASE_DIR / 'subdir'
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Security settings
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-pu36nvw=^s-o1zu@3dpe&u-5-^3qd@&o^1%)nmvm88!2dw7g=#")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")

CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "False").lower() == "true"

# Application definition
INSTALLED_APPS = [
    'daphne',
    'eticketauth',
    'corsheaders',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'channels',
    'rest_framework',
    'django_filters',
    'bus',
    'seat',
    'city',
    'routes',
    'schedule',
    'booking',
    'payment',
    'hiace',
    'dashboard',
    'appsettings',
    'bus_location'
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'eticket.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'eticket.wsgi.application'
ASGI_APPLICATION = 'eticket.asgi.application'

# Channel layers with Redis
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [
                {
                    "address": f"redis://{os.getenv('REDIS_HOST', '127.0.0.1')}:{os.getenv('REDIS_PORT', 6379)}/0",
                    "socket_timeout": 30,
                    "socket_connect_timeout": 5,
                }
            ],
        },
    },
}

REDIS_URL = f"redis://{os.getenv('REDIS_HOST', '127.0.0.1')}:{os.getenv('REDIS_PORT', 6379)}/1"

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = "Asia/Kathmandu"
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = 'static/'
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

AUTH_USER_MODEL = "eticketauth.User"

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# Esewa Details
ESEWA_PAYMENT_URL = os.getenv("ESEWA_PAYMENT_URL", "https://rc-epay.esewa.com.np/api/epay/main/v2/form")
ESEWA_PRODUCT_CODE = os.getenv("ESEWA_PRODUCT_CODE", "EPAYTEST")
ESEWA_SECRET_KEY = os.getenv("ESEWA_SECRET_KEY", "8gBm/:&EnhH.1/q")
ESEWA_SUCCESS_URL = os.getenv("ESEWA_SUCCESS_URL", "http://yourdomain.com/api/payment/esewa/success/")
ESEWA_FAILURE_URL = os.getenv("ESEWA_FAILURE_URL", "http://yourdomain.com/api/payment/esewa/failure/")

# Khalti Details
KHALTI_INITIATE_URL = os.getenv("KHALTI_INITIATE_URL", "https://dev.khalti.com/api/v2/epayment/initiate/")
WEBSITE_URL = os.getenv("WEBSITE_URL", "http://example.com/")
RETURN_URL = os.getenv("RETURN_URL", "https://example.com/")
KHALTI_SECRET_KEY = os.getenv("KHALTI_SECRET_KEY", "ddbaf9fe88e04fe2a133ec39a57fd731")