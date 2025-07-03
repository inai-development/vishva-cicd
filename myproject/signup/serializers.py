from rest_framework import serializers
from signup.models import SignupUser
from django.contrib.auth.password_validation import validate_password as django_validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
import re

# ✅ Common reusable password validator
def validate_strong_password(value):
    if len(value) < 8:
        raise serializers.ValidationError("Password must be at least 8 characters long.")
    if not re.search(r'[A-Z]', value):
        raise serializers.ValidationError("Password must contain at least one uppercase letter.")
    if not re.search(r'[a-z]', value):
        raise serializers.ValidationError("Password must contain at least one lowercase letter.")
    if not re.search(r'\d', value):
        raise serializers.ValidationError("Password must contain at least one digit.")
    if not re.search(r'[!@#$%^&*(),.?\":{}|<>]', value):
        raise serializers.ValidationError("Password must contain at least one special character.")
    
    try:
        django_validate_password(value)
    except DjangoValidationError as e:
        raise serializers.ValidationError(e.messages)
    
# ✅ Signup Serializer with strong validation
class SignupUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, min_length=8)

    class Meta:
        model = SignupUser
        fields = ['id', 'username', 'email', 'password']

    def validate_email(self, value):
        if not value:
            raise serializers.ValidationError("Email is required.")
        if SignupUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered.")
        return value

    def validate_password(self, value):
        return validate_strong_password(value)

    def create(self, validated_data):
        return SignupUser.objects.create_user(**validated_data)