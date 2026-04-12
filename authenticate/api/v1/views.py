from django.contrib.auth import authenticate
from django.core.cache import cache
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer
from rest_framework import status, serializers
from rest_framework.exceptions import Throttled
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from authenticate.permissions import ClientCredentialPermission
from authenticate.utils import (verify_signed_token,
                                verify_otp_code,
                                sign_user_name, generate_otp)
from rest_framework.permissions import AllowAny

from authenticate.api.v1.serializers import LoginAPIViewSerializer
from config.client.mail_engine import EmailEngine
from users.models import User
from oauth2_provider.contrib.rest_framework import OAuth2Authentication


@extend_schema(
    tags=['Auth'],
    summary='Step 1 — Login with email & password',
    description='Validates credentials and sends a 6-digit OTP to the user\'s email. Returns a signed `otp_session` token to be used in the verify-otp step.',
    request=LoginAPIViewSerializer,
    responses={
        200: inline_serializer('LoginResponse', fields={
            'message': serializers.CharField(),
            'otp_session': serializers.CharField(),
            'expires_in': serializers.IntegerField(),
        }),
        401: OpenApiResponse(description='Invalid email or password'),
        403: OpenApiResponse(description='Account disabled or not verified'),
    }
)
class LoginAPIView(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [ClientCredentialPermission]
    throttle_scope = 'login'
    throttle_classes = [ScopedRateThrottle]
    serializers = LoginAPIViewSerializer

    def post(self, request):
        serializer = self.serializers(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        user = authenticate(request=request,email=email, password=password)
        if user is not None:
            if not user.is_active:
                return Response({
                    "error": "Your account has been disabled. Please contact the admin."
                }, status=status.HTTP_403_FORBIDDEN)

            profile = getattr(user, 'business_profile', None) or getattr(user,
                'buyer_profile', None)

            if profile and not profile.is_active:
                return Response({
                    "error": "Please verify your account to continue.",
                    "code": "profile_not_verified"
                }, status=status.HTTP_403_FORBIDDEN)

            otp = generate_otp()
            print("---otp-------->",otp)

            is_otp_sent = EmailEngine.send_otp(email, otp, email)
            if True:
                cache.set(f"otp_{email}", otp, timeout=300)

                otp_session = sign_user_name(email)

                return Response({
                    "message": "OTP sent successfully",
                    "otp_session": otp_session,
                    "expires_in": 300
                }, status=200)

        return Response({"error": "Invalid email or password"}, status=status.HTTP_401_UNAUTHORIZED)


@extend_schema(
    tags=['Auth'],
    summary='Step 2 — Verify OTP',
    description=(
        'Verifies the OTP against the signed session token.\n\n'
        '**action values:**\n'
        '- `login` — completes login, returns JWT tokens\n'
        '- `user_activation` — activates a newly registered account'
    ),
    request=inline_serializer('VerifyOtpRequest', fields={
        'otp': serializers.CharField(),
        'verification_token': serializers.CharField(),
        'action': serializers.ChoiceField(choices=['login', 'user_activation']),
    }),
    responses={
        200: inline_serializer('TokenResponse', fields={
            'access': serializers.CharField(),
            'refresh': serializers.CharField(),
            'role': serializers.ChoiceField(choices=['business', 'buyer']),
            'user_id': serializers.IntegerField(),
            'message': serializers.CharField(),
        }),
        400: OpenApiResponse(description='Invalid or expired OTP'),
        401: OpenApiResponse(description='Invalid or expired verification token'),
    }
)
class VerifyOtpAPIView(APIView):
    permission_classes = [ClientCredentialPermission]

    def post(self, request):
        user_input_otp = request.data.get('otp')
        token = request.data.get('verification_token')
        action = request.data.get('action')

        if not user_input_otp or not token:
            return Response({"error": "OTP and Token are required"}, status=400)

        # 1. Extract email from signed token
        signed_dict = verify_signed_token(token, salt="ecom.otp.session")
        if not signed_dict:
            return Response({"error": "Invalid or expired verification token"},
                status=401)

        email = signed_dict.get('email')
        if not email:
            return Response({"error": "Token payload corrupt"}, status=400)

        # 2. Verify OTP against Redis
        if not verify_otp_code(email, user_input_otp):
            return Response({"error": "Invalid or expired OTP"}, status=400)

        try:
            user = User.objects.get(email=email)
            print("user------------>",user)

            # 3. Handle Profile Activation (The Dual-Flag Logic)
            # Find which profile exists for this user
            profile = getattr(user, 'business_profile', None) or getattr(user,
                'buyer_profile', None)

            if not profile:
                return Response({"error": "Profile not found for this user"},
                    status=404)

            if action=="user_activation":
                if profile.is_active:
                    return Response({"message": "Profile is already active."},
                        status=400)

                # Flip the Profile flag, NOT the User flag
                profile.is_active = True
                profile.save()
                message = "Account verified and activated successfully!"

            elif action=="login":
                # Check if they are trying to login without having verified first
                if not profile.is_active:
                    return Response(
                        {"error": "Please verify your account first."},
                        status=403)
            else:
                return Response({"error": "Invalid action"}, status=400)

            # 4. Generate JWT Tokens
            refresh = RefreshToken.for_user(user)

            # Add the role to the response for the frontend
            role = "business" if hasattr(user, 'business_profile') else "buyer"

            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "role": role,
                "user_id": user.id,
                "message": "OTP is verified and successfully!"
            }, status=200)

        except User.DoesNotExist:
            return Response({"error": "User record not found"}, status=404)

@extend_schema(
    tags=['Auth'],
    summary='Resend OTP',
    description='Resends the OTP to the user\'s email. Use `action=user_activation` for new accounts, `action=login` for existing users.',
    request=inline_serializer('ResendOtpRequest', fields={
        'email': serializers.EmailField(),
        'action': serializers.ChoiceField(choices=['login', 'user_activation']),
    }),
    responses={
        200: inline_serializer('ResendOtpResponse', fields={
            'message': serializers.CharField(),
            'verification_token': serializers.CharField(),
        }),
        403: OpenApiResponse(description='Account disabled or not yet activated'),
    }
)
class ResendOTPView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'verify_otp'
    throttle_classes = [ScopedRateThrottle]

    def post(self, request):
        email = request.data.get('email')
        action = request.data.get('action')

        if not email:
            return Response({"error": "Email is required"}, status=400)

        try:
            user = User.objects.get(email=email)

            if action=="user_activation":
                if user.is_active:
                    return Response({"message": "Account is already active."},
                        status=400)
                success_msg = "A new activation code has been sent."

            elif action=="login":
                # If they are inactive but have logged in before, they are likely banned
                if not user.is_active and user.last_login is not None:
                    return Response({
                        "error": "This account has been disabled. Please contact support."},
                        status=403)

                # If they are inactive and NEVER logged in, they need to activate first
                if not user.is_active and user.last_login is None:
                    return Response({
                        "error": "Please activate your account before logging in."},
                        status=403)

                success_msg = "A new login code has been sent."

            else:
                return Response({"error": "Invalid action"}, status=400)

            # Cleanest approach: Use the utility that does both
            token = send_otp_code(email)

            return Response({
                "message": success_msg,
                "verification_token": token
            }, status=200)

        except User.DoesNotExist:
            # Masking for security
            return Response({
                "message": "If this email is in our system, a new OTP has been sent."
            }, status=200)

    def throttled(self, request, wait):
        # Professional touch: Tell them exactly how long to wait (in minutes)
        wait_minutes = max(1, round(wait / 60))

        throttle_msg = (
            f"Too many attempts. Please try again in {wait_minutes} minutes, "
            "or contact support if you continue to have trouble.")

        raise Throttled(detail={
            "message": throttle_msg,
            "available_in_seconds": round(wait),
            "throttleType": "verify_otp"
        })