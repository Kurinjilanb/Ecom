from rest_framework import serializers
from users.models import User, BusinessProfile, BuyerProfile
from django.db import transaction

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'date_joined']

class BusinessRegistrationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True,
        style={'input_type': 'password'})

    class Meta:
        model = BusinessProfile
        fields = ['email', 'password', 'store_name', 'business_address',
                  'tax_id']

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "A user with this email already exists.")
        return value

    def create(self, validated_data):
        """
        We use an atomic transaction so that if the BusinessProfile fails,
        the User isn't created (prevents "ghost" users).
        """
        email = validated_data.pop('email')
        password = validated_data.pop('password')

        # 1. Create the Core User
        user = User.objects.create_user(
            email=email,
            password=password,
        is_active = False
        )
        business_profile = BusinessProfile.objects.create(
            user=user,
            **validated_data
        )

        return business_profile


class BuyerRegistrationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = BuyerProfile
        fields = [
            'email', 'password', # Must be included here to be validated
            'default_shipping_address',
            'date_of_birth',
        ]
        read_only_fields = ['loyalty_points']

    def validate(self, data):
        # Check if email exists
        if User.objects.filter(email=data.get('email')).exists():
            raise serializers.ValidationError({"email": "This email is already registered."})
        return data

    def create(self, validated_data):
        email = validated_data.pop('email')
        password = validated_data.pop('password')

        # 1. Create the Core User (is_active=False until OTP is verified)
        user = User.objects.create_user(
            email=email,
            password=password,
            is_active=False
        )

        # 3. Create the Buyer Specific Profile
        buyer_profile = BuyerProfile.objects.create(
            user=user,
            **validated_data
        )

        return buyer_profile