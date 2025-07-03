from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

class SignupUserManager(BaseUserManager):
    def create_user(self, username, email, password=None):
        if not email:
            raise ValueError('Email required')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email)
        user.set_password(password)
        user.save(using=self._db)
        return user

class SignupUser(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)

    otp = models.CharField(max_length=6, blank=True, null=True)          # ✅ OTP
    otp_created_at = models.DateTimeField(blank=True, null=True)         # ✅ OTP timestamp
    phone_number = models.CharField(max_length=15, blank=True, null=True) # ✅ Phone for SMS OTP

    objects = SignupUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email
