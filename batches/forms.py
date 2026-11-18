from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q

from accounts.forms import apply_control_classes

from .models import FermentType, JarBatch, RatioTemplate


class RatioCalculatorForm(forms.Form):
    """Interactive form for calculating brine salt, sugar, and jar working volumes."""

    ratio_template = forms.ModelChoiceField(
        queryset=RatioTemplate.objects.select_related("ferment_type").filter(
            is_active=True, ferment_type__is_active=True
        ),
        required=False,
        empty_label="Custom ratio (enter percentages below)",
        label="Load a standard template (optional)",
    )
    jar_capacity = forms.DecimalField(
        min_value=Decimal("10.00"),
        max_digits=10,
        decimal_places=2,
        initial=Decimal("1000.00"),
        label="Jar capacity (mL)",
        help_text="Total nominal volume of the vessel in milliliters (e.g. 1000 for 1 L).",
    )
    headspace_percent = forms.DecimalField(
        min_value=Decimal("0.00"),
        max_value=Decimal("50.00"),
        max_digits=5,
        decimal_places=2,
        initial=Decimal("15.00"),
        label="Headspace allowance (%)",
        help_text="Recommended 10–20% headspace for CO₂ expansion and weights.",
    )
    produce_weight_g = forms.DecimalField(
        min_value=Decimal("0.00"),
        max_digits=10,
        decimal_places=2,
        required=False,
        initial=Decimal("0.00"),
        label="Produce / solid ingredient weight (g, optional)",
        help_text="Include solid vegetable weight when calculating total salt across produce + brine.",
    )
    salt_ratio = forms.DecimalField(
        min_value=Decimal("0.00"),
        max_value=Decimal("100.00"),
        max_digits=5,
        decimal_places=2,
        required=False,
        label="Salt percentage (%)",
    )
    sugar_ratio = forms.DecimalField(
        min_value=Decimal("0.00"),
        max_value=Decimal("100.00"),
        max_digits=5,
        decimal_places=2,
        required=False,
        label="Sugar percentage (%)",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_control_classes(self.fields)

    def clean(self):
        cleaned_data = super().clean()
        template = cleaned_data.get("ratio_template")
        salt_ratio = cleaned_data.get("salt_ratio")
        sugar_ratio = cleaned_data.get("sugar_ratio")

        if template:
            if salt_ratio is None and template.salt_ratio is not None:
                cleaned_data["salt_ratio"] = template.salt_ratio
            if sugar_ratio is None and template.sugar_ratio is not None:
                cleaned_data["sugar_ratio"] = template.sugar_ratio

        if (
            cleaned_data.get("salt_ratio") is None
            and cleaned_data.get("sugar_ratio") is None
        ):
            raise ValidationError(
                "Enter a salt percentage, a sugar percentage, or select a ratio template."
            )
        return cleaned_data


class FermentTypeForm(forms.ModelForm):
    """Administrator form for creating or updating standard ferment categories."""

    class Meta:
        model = FermentType
        fields = (
            "name",
            "description",
            "default_cadence",
            "recommended_vessel",
            "is_active",
        )
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Ginger Bug"}),
            "description": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Describe the fermentation style and baseline."}
            ),
            "default_cadence": forms.TextInput(
                attrs={"placeholder": "e.g. Daily feed · 5–7d"}
            ),
            "recommended_vessel": forms.TextInput(
                attrs={"placeholder": "e.g. Glass mason jar"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != "is_active":
                apply_control_classes({name: field})
            else:
                field.widget.attrs["class"] = "form-check-input"


class RatioTemplateForm(forms.ModelForm):
    """Administrator form for creating or updating standard salt/sugar ratio presets."""

    class Meta:
        model = RatioTemplate
        fields = (
            "ferment_type",
            "name",
            "salt_ratio",
            "sugar_ratio",
            "default_duration_days",
            "is_active",
        )
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. 2.5% Spicy Radish Brine"}),
            "salt_ratio": forms.NumberInput(attrs={"step": "0.01", "min": "0", "max": "100"}),
            "sugar_ratio": forms.NumberInput(attrs={"step": "0.01", "min": "0", "max": "100"}),
            "default_duration_days": forms.NumberInput(attrs={"min": "0"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != "is_active":
                apply_control_classes({name: field})
            else:
                field.widget.attrs["class"] = "form-check-input"


class JarBatchForm(forms.ModelForm):
    """Owner-scoped form for creating and editing fermentation jar batches."""

    class Meta:
        model = JarBatch
        fields = (
            "jar_id",
            "batch_name",
            "ferment_type",
            "ratio_template",
            "jar_capacity",
            "vessel_material",
            "start_date",
            "target_duration_days",
            "salt_ratio",
            "sugar_ratio",
            "status",
            "completion_date",
            "ingredients_notes",
        )
        widgets = {
            "jar_id": forms.TextInput(attrs={"placeholder": "e.g. JAR-01"}),
            "batch_name": forms.TextInput(attrs={"placeholder": "e.g. Autumn Red Cabbage Kraut"}),
            "jar_capacity": forms.NumberInput(
                attrs={"step": "1", "min": "1", "placeholder": "e.g. 1000"}
            ),
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "target_duration_days": forms.NumberInput(attrs={"min": "0"}),
            "salt_ratio": forms.NumberInput(
                attrs={"step": "0.01", "min": "0", "max": "100", "placeholder": "e.g. 2.20"}
            ),
            "sugar_ratio": forms.NumberInput(
                attrs={"step": "0.01", "min": "0", "max": "100", "placeholder": "e.g. 8.00"}
            ),
            "completion_date": forms.DateInput(attrs={"type": "date"}),
            "ingredients_notes": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "List produce weights, water volume, aromatics, starter, and batch notes.",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        active_types = Q(is_active=True)
        if self.instance and self.instance.pk and self.instance.ferment_type_id:
            active_types |= Q(pk=self.instance.ferment_type_id)
        self.fields["ferment_type"].queryset = FermentType.objects.filter(active_types)

        active_templates = Q(is_active=True, ferment_type__is_active=True)
        if self.instance and self.instance.pk and self.instance.ratio_template_id:
            active_templates |= Q(pk=self.instance.ratio_template_id)
        self.fields["ratio_template"].queryset = RatioTemplate.objects.select_related(
            "ferment_type"
        ).filter(active_templates)
        self.fields["ratio_template"].required = False
        self.fields["ratio_template"].empty_label = "Custom ratios (manual)"

        self.fields["jar_capacity"].label = "Jar capacity (mL)"
        self.fields["jar_id"].label = "Jar ID"
        self.fields["target_duration_days"].label = "Target duration (days)"
        self.fields["salt_ratio"].label = "Salt ratio (%)"
        self.fields["sugar_ratio"].label = "Sugar ratio (%)"

        apply_control_classes(self.fields)

    def clean_jar_id(self) -> str:
        jar_id = (self.cleaned_data.get("jar_id") or "").strip()
        if not jar_id:
            raise ValidationError("Enter a unique jar identifier (e.g. JAR-01).")
        owner = self.user or getattr(self.instance, "user", None)
        if owner is not None:
            existing = JarBatch.objects.filter(user=owner, jar_id__iexact=jar_id)
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise ValidationError(
                    f"You already have a batch using jar ID '{jar_id}'. Choose another label."
                )
        return jar_id

    def clean_jar_capacity(self) -> Decimal:
        capacity = self.cleaned_data.get("jar_capacity")
        if capacity is None or capacity <= 0:
            raise ValidationError("Jar capacity must be greater than zero.")
        return capacity

    def clean_salt_ratio(self):
        value = self.cleaned_data.get("salt_ratio")
        if value is not None and (value < 0 or value > 100):
            raise ValidationError("Salt percentage must be between 0% and 100%.")
        return value

    def clean_sugar_ratio(self):
        value = self.cleaned_data.get("sugar_ratio")
        if value is not None and (value < 0 or value > 100):
            raise ValidationError("Sugar percentage must be between 0% and 100%.")
        return value

    def clean(self):
        cleaned_data = super().clean()
        ferment_type = cleaned_data.get("ferment_type")
        ratio_template = cleaned_data.get("ratio_template")
        start_date = cleaned_data.get("start_date")
        status = cleaned_data.get("status")
        completion_date = cleaned_data.get("completion_date")

        if ratio_template and ferment_type and ratio_template.ferment_type_id != ferment_type.id:
            self.add_error(
                "ratio_template",
                f"'{ratio_template.name}' belongs to {ratio_template.ferment_type.name}, not {ferment_type.name}.",
            )

        if ratio_template:
            if cleaned_data.get("salt_ratio") is None and ratio_template.salt_ratio is not None:
                cleaned_data["salt_ratio"] = ratio_template.salt_ratio
            if cleaned_data.get("sugar_ratio") is None and ratio_template.sugar_ratio is not None:
                cleaned_data["sugar_ratio"] = ratio_template.sugar_ratio

        if status == JarBatch.Status.COMPLETED and not completion_date:
            self.add_error(
                "completion_date",
                "Completion / bottling date is required when marking a batch Completed.",
            )
        elif status != JarBatch.Status.COMPLETED and completion_date:
            self.add_error(
                "completion_date",
                "Clear the completion date unless the batch status is Completed.",
            )

        if completion_date and start_date and completion_date < start_date:
            self.add_error(
                "completion_date",
                "Completion date cannot be earlier than the start date.",
            )

        return cleaned_data
