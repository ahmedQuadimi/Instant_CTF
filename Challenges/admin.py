from django.contrib import admin

from .models import Challenge

# Register your models here.


_MODEL_FIELD_NAMES = {f.name for f in Challenge._meta.fields}
_STATUS_FIELD = "status" if "status" in _MODEL_FIELD_NAMES else "state"


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ("name", "category", _STATUS_FIELD, "release_time", "solves_count")
    list_filter = (_STATUS_FIELD, "category")
    list_editable = (_STATUS_FIELD,)
    search_fields = ("name", "description")
    readonly_fields = ("solves_count",)

    def get_fields(self, request, obj=None):
        fields = [
            "event",
            "name",
            "category",
            "description",
            "flag_hash",
            "release_time",
        ]

        for optional_field in ("connection_info", "attachment", _STATUS_FIELD):
            if optional_field in _MODEL_FIELD_NAMES and optional_field not in fields:
                fields.append(optional_field)

        return fields
