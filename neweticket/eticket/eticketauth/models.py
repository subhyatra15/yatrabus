from django.db import models
from django.contrib.auth.models import AbstractUser
from .managers import UserManager

ROLE_CHOICES = (
    ('A', 'ADMIN'),
    ('P', 'PASSENGER'),
    ('D', 'DRIVER'),
)

class User(AbstractUser):
    username = None
    phone = models.CharField(max_length=15, unique=True)
    image = models.ImageField(upload_to="images/", null=True, blank=True)
    role = models.CharField(max_length=1, choices=ROLE_CHOICES, default='P')
    fullName = models.CharField(
    max_length=255,
    null=True,
    blank=True
)

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return f"{self.fullName} ({self.phone}) {self.role}"