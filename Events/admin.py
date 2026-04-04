from django.contrib import admin

from .models import Event, EventRoster

# Register your models here.


class RosterInline(admin.TabularInline):
    model = EventRoster
    extra = 1


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "organization",
        "start_time",
        "end_time",
        "visibility",
        "scoring_strategy",
    )
    list_filter = ("visibility", "scoring_strategy", "organization")
    search_fields = ("title",)
    inlines = [RosterInline]


@admin.register(EventRoster)
class EventRosterAdmin(admin.ModelAdmin):
    list_display = ("user", "team", "event")
    list_filter = ("event", "team")
    search_fields = ("user__username", "team__name")
