from django.contrib import admin

from Events.models import EventRoster
from .models import Solve, Submission

# Register your models here.


_SUBMISSION_READONLY_FIELDS = tuple(field.name for field in Submission._meta.fields)
_SOLVE_READONLY_FIELDS = tuple(field.name for field in Solve._meta.fields)


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("user", "challenge", "is_correct", "submitted_at")
    list_filter = ("is_correct", "challenge__event", "team")
    search_fields = (
        "provided_flag",
        "user__username",
        "user__email",
        "challenge__name",
    )
    date_hierarchy = "timestamp"
    list_select_related = ("user", "team", "challenge")

    @admin.display(description="submitted_at", ordering="timestamp")
    def submitted_at(self, obj):
        return obj.timestamp


@admin.register(Solve)
class SolveAdmin(admin.ModelAdmin):
    list_display = ("team", "challenge", "created_at")
    list_filter = ("challenge__event", "team")
    search_fields = (
        "team__name",
        "challenge__name",
        "submission__user__username",
        "submission__user__email",
    )
    date_hierarchy = "timestamp"
    list_select_related = (
        "team",
        "challenge",
        "challenge__event",
        "submission",
        "submission__user",
    )

    @admin.display(description="team", ordering="team__name")
    def team(self, obj):
        roster = (
            EventRoster.objects.filter(
                user=obj.submission.user,
                event=obj.challenge.event,
            )
            .select_related("team")
            .first()
        )
        if roster and roster.team:
            return roster.team
        return obj.team

    @admin.display(description="created_at", ordering="timestamp")
    def created_at(self, obj):
        return obj.timestamp
