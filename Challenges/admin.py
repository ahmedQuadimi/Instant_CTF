from django.contrib import admin
from .models import Challenge

@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "status", "release_time", "solves_count")
    list_filter = ("status", "category")
    list_editable = ("status",)
    search_fields = ("name", "description")
    readonly_fields = ("solves_count",)

    def get_fields(self, request, obj=None):
        # The base fields that always exist
        fields = [
            "event",
            "name",
            "category",
            "description",
            "flag_hash",
            "release_time",
            "status",
        ]

        # Dynamically append the optional fields if they exist in the model
        # (This is still safe to keep in case you drop attachment/connection_info later)
        _MODEL_FIELD_NAMES = {f.name for f in Challenge._meta.fields}
        for optional_field in ("connection_info", "attachment"):
            if optional_field in _MODEL_FIELD_NAMES and optional_field not in fields:
                fields.append(optional_field)

        return fields