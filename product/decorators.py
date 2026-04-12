from functools import wraps
from rest_framework import status
from rest_framework.response import Response
from users.models import BusinessProfile


def is_merchant_account(view_func):
    @wraps(view_func)
    def _wrapped_view(instance, request, *args, **kwargs):
        # 1. Check if the user is authenticated
        if not request.user or not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication required."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        try:
            business_profile = BusinessProfile.objects.get(user=request.user)
        except BusinessProfile.DoesNotExist:
            return Response(
                {
                    "detail": "Merchant profile not found. Please complete your registration."},
                status=status.HTTP_403_FORBIDDEN
            )

        if not business_profile.is_active:
            return Response(
                {
                    "detail": "Merchant profile is inactive. Please contact support."},
                status=status.HTTP_403_FORBIDDEN
            )
        request.business_profile = business_profile

        return view_func(instance, request, *args, **kwargs)

    return _wrapped_view