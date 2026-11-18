from django.core.exceptions import ValidationError
from django.db import models


class FermentType(models.Model):
    """Standard fermentation category managed as reference data."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    default_cadence = models.CharField(
        max_length=100,
        blank=True,
        help_text="e.g. Daily burp · 14–28d",
    )
    recommended_vessel = models.CharField(
        max_length=100,
        blank=True,
        help_text="e.g. Glass mason jar",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ferment_types"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class RatioTemplate(models.Model):
    """Standard salt and sugar ratio preset linked to a FermentType."""

    ferment_type = models.ForeignKey(
        FermentType,
        on_delete=models.CASCADE,
        related_name="ratio_templates",
    )
    name = models.CharField(max_length=100)
    salt_ratio = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Salt percentage by weight/volume (0–100%).",
    )
    sugar_ratio = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Sugar percentage by weight/volume (0–100%).",
    )
    default_duration_days = models.PositiveIntegerField(default=14)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ratio_templates"
        ordering = ["ferment_type__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["ferment_type", "name"],
                name="unique_template_per_ferment_type",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(salt_ratio__isnull=True)
                    | (models.Q(salt_ratio__gte=0) & models.Q(salt_ratio__lte=100))
                ),
                name="ratio_template_salt_range",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(sugar_ratio__isnull=True)
                    | (models.Q(sugar_ratio__gte=0) & models.Q(sugar_ratio__lte=100))
                ),
                name="ratio_template_sugar_range",
            ),
        ]

    def clean(self):
        super().clean()
        if self.salt_ratio is None and self.sugar_ratio is None:
            raise ValidationError(
                "Provide at least a salt ratio or a sugar ratio percentage for a template."
            )

    def ratio_summary(self) -> str:
        parts = []
        if self.salt_ratio is not None:
            parts.append(f"{self.salt_ratio}% salt")
        if self.sugar_ratio is not None:
            parts.append(f"{self.sugar_ratio}% sugar")
        return " · ".join(parts) if parts else "Custom"

    def __str__(self) -> str:
        return f"{self.ferment_type.name} — {self.name} ({self.ratio_summary()})"
