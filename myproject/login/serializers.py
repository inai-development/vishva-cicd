# login/serializers.py
from rest_framework import serializers
from django.contrib.auth import authenticate
from signup.models import SignupUser
from signup.serializers import validate_strong_password

# ✅ Login Serializer
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(request=self.context.get('request'), email=email, password=password)
            if not user:
                raise serializers.ValidationError("Invalid email or password.")
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError("Must include 'email' and 'password'.")

# ✅ Request OTP Serializer
class RequestOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()

# ✅ Reset Password Serializer with strong validation
class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email")
        otp = attrs.get("otp")
        new_password = attrs.get("new_password")

        try:
            user = SignupUser.objects.get(email=email)
        except SignupUser.DoesNotExist:
            raise serializers.ValidationError({"email": "User with this email does not exist."})

        if not user.otp or user.otp != otp:
            raise serializers.ValidationError({"otp": "Invalid or expired OTP."})

        # ✅ Strong password validation
        validate_strong_password(new_password)

        # ✅ Set new password
        user.set_password(new_password)
        user.otp = None   # Expire OTP after use
        user.save()

        attrs['user'] = user
        return attrs