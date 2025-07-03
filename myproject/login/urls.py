from django.urls import path
from .views import LoginView, RequestOTPView, ResetPasswordView

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('request-otp/', RequestOTPView.as_view()),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
]
