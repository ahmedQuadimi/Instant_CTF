from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.


class User(AbstractUser):
    elo = models.IntegerField(default=0, db_index=True)

    def __str__(self):
        return self.username
