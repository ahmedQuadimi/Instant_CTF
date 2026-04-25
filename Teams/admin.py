from django.contrib import admin

from .models import Team, TeamJoinRequest, TeamMembership


# Register your models here.
@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "captain", "global_rating", "is_public")
    list_filter = ("is_public",)
    search_fields = ("name", "captain__username")


@admin.register(TeamJoinRequest)
class TeamJoinRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "team", "status")
    list_filter = ("status",)


@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "team")
    list_filter = ("team",)