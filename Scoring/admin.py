from django.contrib import admin

from .models import Solve, Submission

# Register your models here.


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("team", "user", "challenge", "is_correct", "timestamp")
    list_filter = ("is_correct", "challenge__event", "team")
    search_fields = ("provided_flag", "user__username", "team__name")

    def has_change_permission(self, request, obj=None):
        return False  # Submissions are an immutable log


@admin.register(Solve)
class SolveAdmin(admin.ModelAdmin):
    list_display = ("team", "challenge", "timestamp")
    list_filter = ("challenge__event", "team")
    search_fields = ("team__name", "challenge__name")

    def has_change_permission(self, request, obj=None):
        return False  # Solves are immutable
