from rest_framework.permissions import BasePermission
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed


class ClientCredentialPermission(BasePermission):
    """
    Custom permission class for oauth2
    since we use client credentials grant type there wont be a user associated
    with the oauth token so we are overriding has permission method.
    Note: Use this permission class for landing page, gift code validation,
    refresh token and gift receiver update endpoints.
    All other endpoints should be protected with JWT Token based authentication
    """

    def has_permission(self, request, view):
        if request.auth is None:
            return False
        grant_type = request.auth.application.get_authorization_grant_type_display()
        if request.user is None and grant_type == 'Client credentials':
            return True
        else:
            return False


class IsAuthenticatedCode(BasePermission):
    """
    Allows access only to authenticated activation codes.
    This method is written in this manner since we made authentication based
     on activation code
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_active)

class IsMerchant(BasePermission):
    """
    Step 1: Is the user a verified Business?
    """
    message = "Only verified business accounts can perform this action."

    def has_permission(self, request, view):
        user = request.user
        print("user", user)
        return bool(
            user.is_authenticated and
            hasattr(user, 'business_profile') and
            user.business_profile.is_active
        )

class IsOwner(BasePermission):
    """    """
    message = "You do not have permission to modify this product."

    def has_object_permission(self, request, view, obj):
        # In your model, Product.merchant links to BusinessProfile
        return obj.merchant == request.user.business_profile

class CustomUserJWTAuthentication(JWTAuthentication):

    def authenticate(self, request):
        user_and_token = super().authenticate(request)

        if user_and_token is None:
            return None

        user, validated_token = user_and_token

        if user.last_password_changed and validated_token[
            'iat'] < user.last_password_changed.timestamp():
            raise AuthenticationFailed(
                ('Token is invalid due to password change.'))

        return user, validated_token
