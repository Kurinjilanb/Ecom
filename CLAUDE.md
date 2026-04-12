


# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Local development
python manage.py runserver

# Run migrations
python manage.py migrate

# Seed the database
python seed.py

# Docker (runs migrate + server via honcho/Procfile)
docker compose up

# Run a single test
python manage.py test <app>.<TestClass>.<test_method>
# e.g. python manage.py test authenticate.tests.LoginTests.test_invalid_password
```

The `DJANGO_SETTINGS_MODULE` env var controls which settings file is used. For local dev it should point to `config.settings.development`.

## Architecture

### Apps

| App | Responsibility |
|---|---|
| `users` | Custom `User` model (email-based auth), `BuyerProfile`, `BusinessProfile` |
| `authenticate` | Login, OTP verify/resend, permissions, JWT auth |
| `product` | Product catalog: categories, products, variants, images |
| `config` | Django settings (split by environment), root URLs, mail engine |

### Auth Flow

Login is a two-step OTP process:
1. `POST /auth/api/v1/login/` — validates credentials, sends OTP to email, returns a signed `otp_session` token (via `django.core.signing`)
2. `POST /auth/api/v1/verify-otp/` — verifies OTP from Redis cache + signed token, issues JWT access/refresh tokens

The `LoginAPIView` requires an **OAuth2 client credentials token** (`ClientCredentialPermission`), not a JWT. This means the frontend must first obtain an OAuth token for the app itself before calling login.

### Authentication Classes

All product/user write endpoints use `CustomUserJWTAuthentication` (extends `simplejwt`), which invalidates tokens issued before `last_password_changed`.

The global default authentication in `REST_FRAMEWORK` settings is `OAuth2Authentication` (for public/landing endpoints). Individual views override this with `CustomUserJWTAuthentication`.

### User Profiles

Two profile types hang off `User` via OneToOne:
- `user.business_profile` → `BusinessProfile` (merchants)
- `user.buyer_profile` → `BuyerProfile` (customers)

Use `getattr(user, 'business_profile', None)` when a user's role is unknown. Never use `merchant_profile` — that field does not exist.

### Permissions (`authenticate/permissions.py`)

| Class | Check |
|---|---|
| `IsMerchant` | User has an active `business_profile` |
| `IsOwner` | `obj.merchant == request.user.business_profile` (object-level) |
| `ClientCredentialPermission` | OAuth2 client credentials grant (no user) |

### Product API (`product/api/v1/`)

`ProductViewSet` uses `lookup_field = 'slug'`. Permission matrix:
- `list`, `retrieve` → `AllowAny`
- `create` → `IsAuthenticated + IsMerchant`
- `update`, `partial_update`, `destroy` → `IsAuthenticated + IsMerchant + IsOwner`

Serializer selection per action:
- `list` → `ProductListSerializer`
- `retrieve` → `ProductDetailSerializer`
- `create` → `ProductCreateSerializer` (accepts nested `variants` and `images`)
- `update`/`partial_update` → `ProductUpdateSerializer`

On `create`, set the merchant with `serializer.save(merchant=request.user.business_profile)`.

### URL Structure

```
/auth/api/v1/     → authenticate app
/user/api/v1/     → users app (registration, profile, token refresh, OAuth)
/products/api/v1/ → product app (products, colors, sizes)
```

### Settings

Settings are split: `base.py` → imported by `development.py`, `production.py`, `qa.py`, `sandbox.py`. JWT config (lifetimes, signing key) lives in environment-specific settings files, not base.

### OTP / Cache

OTPs are stored in cache (Redis in Docker, `LocMemCache` in base config) under the key `otp_<email>` with a 300-second TTL. After successful verification the key is deleted.

### Email

Mailpit is used locally (SMTP on port 1025, web UI on port 8025). The `EmailEngine` wrapper lives in `config/client/mail_engine.py`.
