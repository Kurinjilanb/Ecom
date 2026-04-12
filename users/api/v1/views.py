from django.core.cache import cache
from django.db import transaction
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from authenticate.permissions import ClientCredentialPermission
from authenticate.utils import generate_otp
from .serializers import (UserProfileSerializer,
                           BusinessRegistrationSerializer, BuyerRegistrationSerializer)


@extend_schema(tags=['Users'])
class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Get current user profile',
        responses={200: UserProfileSerializer},
    )
    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    @extend_schema(
        summary='Update current user profile',
        request=UserProfileSerializer,
        responses={200: UserProfileSerializer},
    )
    def patch(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


@extend_schema(
    tags=['Users'],
    summary='Register a Merchant account',
    description='Creates a User + BusinessProfile. An OTP is sent to the provided email to verify the account.',
    request=BusinessRegistrationSerializer,
    responses={
        201: OpenApiResponse(description='Account created, OTP sent to email'),
        400: OpenApiResponse(description='Validation errors'),
    }
)
class BusinessRegistrationView(GenericAPIView):
    permission_classes = [ClientCredentialPermission]
    serializer_class = BusinessRegistrationSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            business_profile = serializer.save()
            user = business_profile.user
            otp = generate_otp()
            cache.set(f"otp_{user.email}", otp, timeout=300)

            return Response({
                "message": "Business account created. Please verify the OTP sent to your email.",
                "email": user.email,
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Users'],
    summary='Register a Buyer account',
    description='Creates a User + BuyerProfile. Verify the account using the verify-otp endpoint with `action=user_activation`.',
    request=BuyerRegistrationSerializer,
    responses={
        201: OpenApiResponse(description='Account created, verify via OTP'),
        400: OpenApiResponse(description='Validation errors'),
    }
)
class BuyerRegistrationView(GenericAPIView):
    serializer_class = BuyerRegistrationSerializer
    permission_classes = []

    def post(self, request):
        with transaction.atomic():
            serializer = self.get_serializer(data=request.data)

            if serializer.is_valid():
                email = serializer.validated_data['email']
                profile = serializer.save()

                return Response({
                    "message": "Buyer account created successfully. Please verify your email.",
                    "status": "pending_verification",
                }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)