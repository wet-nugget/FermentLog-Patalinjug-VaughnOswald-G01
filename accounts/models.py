from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """Custom user account for FermentLog supporting Home Fermenter and Administrator roles."""

    class Role(models.TextChoices):
        FERMENTER = "FERMENTER", "Home Fermenter"
        ADMIN = "ADMIN", "Administrator"

    email = models.EmailField("email address", unique=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.FERMENTER,
    )
    contact_number = models.CharField(max_length=25, blank=True)
    preferred_ferment = models.CharField(
        max_length=100,
        blank=True,
        help_text="e.g. Kombucha, Sauerkraut, Kimchi, Hot Sauce",
    )
    bio = models.TextField(max_length=300, blank=True)
    profile_photo = models.ImageField(
        upload_to="profile_photos/",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(role__in=["FERMENTER", "ADMIN"]),
                name="valid_user_role",
            )
        ]

    @property
    def is_fermenter(self) -> bool:
        return self.role == self.Role.FERMENTER

    @property
    def is_administrator(self) -> bool:
        return self.role == self.Role.ADMIN

    @property
    def full_name(self) -> str:
        return self.get_full_name() or self.username

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        if self.is_superuser and self.role != self.Role.ADMIN:
            self.role = self.Role.ADMIN
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.username} ({self.get_role_display()})"
