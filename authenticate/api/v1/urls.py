# apps/authentication/api/v1/urls.py
from django.urls import path

from .views import LoginAPIView, VerifyOtpAPIView, ResendOTPView

urlpatterns = [
    path('login/', LoginAPIView.as_view()),
    path('verify-otp/', VerifyOtpAPIView.as_view()),
    path('resend-otp/', ResendOTPView.as_view()),
]