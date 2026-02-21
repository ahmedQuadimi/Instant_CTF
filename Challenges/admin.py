from django.contrib import admin

from .models import Challenge

# Register your models here.


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "event",
        "category",
        "state",
        "solves_count",
        "release_time",
    )
    list_filter = ("event", "state", "category")
    search_fields = ("name", "description")
    readonly_fields = ("solves_count",)
