from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Admin configuration for FermentLog users."""

    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "is_active",
        "date_joined",
    )
    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("username", "email", "first_name", "last_name", "preferred_ferment")
    ordering = ("-date_joined",)

    fieldsets = UserAdmin.fieldsets + (
        (
            "FermentLog Profile",
            {
                "fields": (
                    "role",
                    "contact_number",
                    "preferred_ferment",
                    "bio",
                    "profile_photo",
                )
            },
        ),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "FermentLog Profile",
            {
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "role",
                    "contact_number",
                    "preferred_ferment",
                )
            },
        ),
    )
