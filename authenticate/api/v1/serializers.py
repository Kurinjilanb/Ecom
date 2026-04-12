from rest_framework import serializers


class LoginAPIViewSerializer(serializers.Serializer):
    email = serializers.EmailField(
        error_messages={
            'required': ('Email field is required.'),
            'blank': ('Email field may not be blank.'),
            'invalid': ('A valid email is required.'),
        }
    )
    password = serializers.CharField(
        error_messages={
            'required': ('Password field is required.'),
            'blank': ('Password field may not be blank.'),
        }
    )
