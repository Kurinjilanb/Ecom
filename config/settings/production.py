import os
from datetime import timedelta
from decouple import config

from .base import *

# ─── Core ────────────────────────────────────────────────────────────────────

DEBUG = False
ENVIRONMENT = 'production'

SECRET_KEY = config('SECRET_KEY')
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*').split(',')

# Trust the proxy's X-Forwarded-Proto header (set by Railway / Render / nginx)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# ─── Static files ─────────────────────────────────────────────────────────────
# WhiteNoise serves static files directly from Django (no nginx needed)

MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = config('MEDIA_URL', default='/media/')
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ─── JWT ─────────────────────────────────────────────────────────────────────

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=10),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ─── Cache (Redis) ────────────────────────────────────────────────────────────
# Railway provides REDIS_URL automatically when you add the Redis plugin.

REDIS_URL = config('REDIS_URL', default='redis://localhost:6379')

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
    }
}

# ─── Email ────────────────────────────────────────────────────────────────────

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='Marketplace Support <noreply@market.com>')

# ─── Stripe ───────────────────────────────────────────────────────────────────

STRIPE_SECRET_KEY = config('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = config('STRIPE_WEBHOOK_SECRET')

# ─── Admin ────────────────────────────────────────────────────────────────────

ADMIN_SITE_HEADER = 'Marketplace Admin'
ADMIN_SITE_TITLE = 'Marketplace'