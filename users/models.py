from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = [
        ("superadmin", "Super Admin"),
        ("admin", "Admin"),
        ("viewer", "Viewer"),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="viewer")

    def is_superadmin(self):
        return self.role == "superadmin"

    def is_admin(self):
        # Superadmins are also admins
        return self.role == "admin" or self.is_superadmin()

    def is_viewer(self):
        return self.role == "viewer"

    def __str__(self):
        return f"{self.username} ({self.role})"
