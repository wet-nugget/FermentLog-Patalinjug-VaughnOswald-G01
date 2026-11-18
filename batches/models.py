from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .calculations import calculate_batch_ratios


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


class JarBatch(models.Model):
    """Owner-scoped fermentation batch and jar vessel record."""

    class Status(models.TextChoices):
        FERMENTING = "FERMENTING", "Fermenting"
        COLD_STORAGE = "COLD STORAGE", "Cold Storage"
        COMPLETED = "COMPLETED", "Completed"

    VESSEL_CHOICES = [
        ("Glass Mason Jar", "Glass Mason Jar"),
        ("Ceramic Crock", "Ceramic Crock"),
        ("Airlock Glass Jar", "Airlock Glass Jar"),
        ("Wide-Mouth Brew Jar", "Wide-Mouth Brew Jar"),
        ("Food-Grade Stoneware", "Food-Grade Stoneware"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="jar_batches",
    )
    ferment_type = models.ForeignKey(
        FermentType,
        on_delete=models.PROTECT,
        related_name="jar_batches",
    )
    ratio_template = models.ForeignKey(
        RatioTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jar_batches",
    )
    jar_id = models.CharField(
        max_length=50,
        help_text="Unique jar label in your inventory, e.g. JAR-01 or KRAUT-A.",
    )
    batch_name = models.CharField(
        max_length=120,
        blank=True,
        help_text="Optional descriptive batch title, e.g. Autumn Caraway Kraut.",
    )
    jar_capacity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Total jar volume in mL (must be greater than 0).",
    )
    vessel_material = models.CharField(
        max_length=50,
        choices=VESSEL_CHOICES,
        default="Glass Mason Jar",
    )
    start_date = models.DateField(default=timezone.localdate)
    target_duration_days = models.PositiveIntegerField(default=14)
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.FERMENTING,
    )
    salt_ratio = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Applied salt percentage (0–100%).",
    )
    sugar_ratio = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Applied sugar percentage (0–100%).",
    )
    ingredients_notes = models.TextField(
        blank=True,
        help_text="Produce weights, aromatics, spices, starter culture source, or prep notes.",
    )
    completion_date = models.DateField(
        null=True,
        blank=True,
        help_text="Required when marking a batch Completed.",
    )
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jar_batches"
        ordering = ["is_archived", "-start_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "jar_id"],
                name="unique_user_jar_id",
            ),
            models.CheckConstraint(
                condition=models.Q(jar_capacity__gt=0),
                name="jar_capacity_gt_zero",
            ),
            models.CheckConstraint(
                condition=models.Q(target_duration_days__gte=0),
                name="target_duration_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=["FERMENTING", "COLD STORAGE", "COMPLETED"]),
                name="valid_batch_status",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(salt_ratio__isnull=True)
                    | (models.Q(salt_ratio__gte=0) & models.Q(salt_ratio__lte=100))
                ),
                name="jar_batch_salt_range",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(sugar_ratio__isnull=True)
                    | (models.Q(sugar_ratio__gte=0) & models.Q(sugar_ratio__lte=100))
                ),
                name="jar_batch_sugar_range",
            ),
        ]

    @property
    def display_title(self) -> str:
        return self.batch_name or f"{self.ferment_type.name} ({self.jar_id})"

    @property
    def elapsed_days(self) -> int:
        end_date = (
            self.completion_date
            if self.status == self.Status.COMPLETED and self.completion_date
            else timezone.localdate()
        )
        return max(0, (end_date - self.start_date).days)

    @property
    def remaining_days(self) -> int:
        return max(0, self.target_duration_days - self.elapsed_days)

    @property
    def progress_percent(self) -> int:
        if self.target_duration_days == 0:
            return 100
        return min(100, round((self.elapsed_days / self.target_duration_days) * 100))

    @property
    def target_ready_date(self):
        return self.start_date + timedelta(days=self.target_duration_days)

    @property
    def is_ready_for_transition(self) -> bool:
        return (
            self.status == self.Status.FERMENTING
            and self.elapsed_days >= self.target_duration_days
        )

    @property
    def ratio_breakdown(self) -> dict:
        return calculate_batch_ratios(
            jar_capacity_ml=self.jar_capacity,
            salt_ratio=self.salt_ratio,
            sugar_ratio=self.sugar_ratio,
        )

    def __str__(self) -> str:
        return f"{self.jar_id} — {self.ferment_type.name} ({self.get_status_display()})"
