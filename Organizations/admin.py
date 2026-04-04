from django.contrib import admin

from .models import Organization, OrganizationMembership

# Register your models here.


class MembershipInline(admin.TabularInline):
    model = OrganizationMembership
    extra = 1


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    inlines = [MembershipInline]
