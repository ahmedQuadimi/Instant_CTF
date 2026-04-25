from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.


class User(AbstractUser):
    ROLE_CHOICES = [
        ("SITE_ADMIN", "Site Admin"),
        ("PLAYER", "Player"),
    ]

    elo = models.IntegerField(default=0, db_index=True)
    site_role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="PLAYER")

    def __str__(self):
        return self.username
