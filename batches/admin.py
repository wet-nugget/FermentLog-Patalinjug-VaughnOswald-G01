from django.contrib import admin

from .models import FermentType, RatioTemplate


@admin.register(FermentType)
class FermentTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "default_cadence", "recommended_vessel", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "description")


@admin.register(RatioTemplate)
class RatioTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "ferment_type",
        "salt_ratio",
        "sugar_ratio",
        "default_duration_days",
        "is_active",
    )
    list_filter = ("ferment_type", "is_active")
    search_fields = ("name", "ferment_type__name")
