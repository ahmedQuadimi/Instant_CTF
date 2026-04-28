from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.


class User(AbstractUser):
    ROLE_CHOICES = [
        ("SITE_ADMIN", "Site Admin"),
        ("PLAYER", "Player"),
    ]

    site_role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="PLAYER")
    profile_image = models.ImageField(
        upload_to="profiles/",
        blank=True,
        null=True,
    )

    def __str__(self):
        return self.username
