from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "elo", "is_staff")
    search_fields = ("username", "email")

    # Adds global_score to the admin edit screen safely
    fieldsets = UserAdmin.fieldsets + (("CTF Stats", {"fields": ("elo",)}),)
