from django.contrib import admin

from .models import FermentType, JarBatch, RatioTemplate


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


@admin.register(JarBatch)
class JarBatchAdmin(admin.ModelAdmin):
    list_display = (
        "jar_id",
        "batch_name",
        "user",
        "ferment_type",
        "jar_capacity",
        "start_date",
        "target_duration_days",
        "status",
        "is_archived",
    )
    list_filter = ("status", "is_archived", "ferment_type", "vessel_material")
    search_fields = ("jar_id", "batch_name", "user__username", "ferment_type__name")
