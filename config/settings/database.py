import os
from urllib.parse import urlparse

# Railway / Render / Heroku provide a single DATABASE_URL.
# Local Docker Compose uses individual POSTGRES_* vars.
DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    _url = urlparse(DATABASE_URL)
    DATABASE_CONFIG = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": _url.path.lstrip('/'),
            "USER": _url.username,
            "PASSWORD": _url.password,
            "HOST": _url.hostname,
            "PORT": _url.port or 5432,
        }
    }
else:
    DATABASE_CONFIG = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "ecommerce_db"),
            "USER": os.getenv("POSTGRES_USER", "postgres"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", "postgres"),
            "HOST": os.getenv("DATABASE_HOST", "localhost"),
            "PORT": os.getenv("DATABASE_PORT", "5432"),
        }
    }