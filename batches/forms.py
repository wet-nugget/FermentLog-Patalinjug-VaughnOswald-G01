from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError

from accounts.forms import apply_control_classes

from .models import FermentType, RatioTemplate


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
