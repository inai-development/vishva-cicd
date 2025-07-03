# login/models.py
from django.db import models
from signup.models import SignupUser
from django.utils import timezone

class LoginRecord(models.Model):

    user = models.ForeignKey(SignupUser, on_delete=models.CASCADE)
    username = models.CharField(max_length=150, null=True, blank=True)
    login_time = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    successful = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} - {self.login_time.strftime('%Y-%m-%d %H:%M:%S')} - {self.login_method}"