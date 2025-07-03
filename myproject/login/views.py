from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
import random
from .serializers import LoginSerializer, RequestOTPSerializer, ResetPasswordSerializer
from signup.models import SignupUser
from .models import LoginRecord
from django.utils import timezone

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)

            # ✅ Save successful login record
            LoginRecord.objects.create(
                user=user,
                username=user.username,
                ip_address=self.get_client_ip(request),
                successful=True,
            )

            return Response({
                "message": f"Login successful for user: {user.username}",
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                }
            }, status=status.HTTP_200_OK)

        # ✅ Save failed login record if user exists
        email = request.data.get("email")
        user = SignupUser.objects.filter(email=email).first()
        if user:
            LoginRecord.objects.create(
                user=user,
                username=user.username,
                ip_address=self.get_client_ip(request),
                successful=False,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_client_ip(self, request):
        """Extract client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class RequestOTPView(APIView):
    def post(self, request):
        serializer = RequestOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        try:
            user = SignupUser.objects.get(email=email)
        except SignupUser.DoesNotExist:
            return Response({"error": "Email not registered"}, status=status.HTTP_400_BAD_REQUEST)

        otp = f"{random.randint(100000, 999999)}"
        user.otp = otp
        user.otp_created_at = timezone.now()
        user.save()

        # TODO: send OTP via email/SMS here
        print(f"OTP for {email} is {otp}")

        return Response({"message": "OTP sent to your email"})


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            return Response({"message": "Password updated successfully."})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)