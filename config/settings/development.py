import os
from datetime import timedelta

from .base import *
from decouple import config


DEBUG = True
SITE_SECURE = False
ENVIRONMENT = 'development'

ADMIN_SITE_HEADER = 'SAAS APP - DEVELOPMENT'
ADMIN_SITE_TITLE = 'SaasApp - DEVELOPMENT'
# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/
STATIC_URL = config('STATIC_URL', '/static/')
STATIC_ROOT = os.path.join(ROOT_DIR, 'static')
STATICFILES_DIRS = [
    os.path.join(ROOT_DIR, 'app_static'),
]

# Media Settings (media url, media root etc)
# https://docs.djangoproject.com/en/3.0/ref/settings/#media-root
MEDIA_URL = config('MEDIA_URL', '/media/')
MEDIA_DIR_NAME = 'media/'
MEDIA_ROOT = os.path.join(ROOT_DIR, MEDIA_DIR_NAME)


SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=10),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,   # each refresh issues a new refresh token
    'BLACKLIST_AFTER_ROTATION': True, # old refresh token becomes invalid immediately
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

STRIPE_SECRET_KEY = config('STRIPE_SECRET_KEY', default='sk_test_placeholder')
STRIPE_WEBHOOK_SECRET = config('STRIPE_WEBHOOK_SECRET', default='')

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# Logic: If running in Docker, host is 'mailpit'. If local, 'localhost'.
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'mailpit')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 1025))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')

# For Mailpit, these are False. For Gmail/SendGrid, these are True.
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'False') == 'True'

DEFAULT_FROM_EMAIL = 'Marketplace Support <noreply@market.com>'


STATIC_URL = config('STATIC_URL', '/static/')
STATIC_ROOT = os.path.join(ROOT_DIR, 'static')
STATICFILES_DIRS = [
    os.path.join(ROOT_DIR, 'app_static'),
]