import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError

from .models import CustomUser

CONTACT_NUMBER_PATTERN = re.compile(r"^[+\d\s().-]+$")


def validate_unique_email(email: str, exclude_pk=None) -> str:
    """Normalize email and verify case-insensitive uniqueness."""
    normalized = (email or "").strip().lower()
    queryset = CustomUser.objects.filter(email__iexact=normalized)
    if exclude_pk is not None:
        queryset = queryset.exclude(pk=exclude_pk)
    if queryset.exists():
        raise ValidationError("An account with this email address already exists.")
    return normalized


def validate_contact_number(contact_number: str) -> str:
    """Validate optional contact number format and minimum digit length."""
    cleaned = (contact_number or "").strip()
    if not cleaned:
        return ""
    if not CONTACT_NUMBER_PATTERN.match(cleaned) or sum(c.isdigit() for c in cleaned) < 7:
        raise ValidationError("Enter a valid contact number with at least 7 digits.")
    return cleaned


def apply_control_classes(fields) -> None:
    """Apply consistent Bootstrap control classes across form widgets."""
    for field in fields.values():
        existing = field.widget.attrs.get("class", "")
        base_class = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
        if base_class not in existing:
            field.widget.attrs["class"] = f"{existing} {base_class}".strip()


class CustomUserCreationForm(UserCreationForm):
    """Registration form for new FermentLog accounts."""

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "contact_number",
            "preferred_ferment",
            "role",
            "password1",
            "password2",
        )
        widgets = {
            "username": forms.TextInput(attrs={"autocomplete": "username", "placeholder": "e.g. brinekeeper"}),
            "first_name": forms.TextInput(attrs={"autocomplete": "given-name", "placeholder": "First name"}),
            "last_name": forms.TextInput(attrs={"autocomplete": "family-name", "placeholder": "Last name"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "you@example.com"}),
            "contact_number": forms.TextInput(
                attrs={"autocomplete": "tel", "placeholder": "e.g. +63 917 555 0142"}
            ),
            "preferred_ferment": forms.TextInput(
                attrs={"placeholder": "e.g. Kombucha, Kimchi, Lacto-Pickles"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
        self.fields["email"].required = True
        self.fields["contact_number"].required = False
        self.fields["preferred_ferment"].required = False
        self.fields["role"].label = "Account role"
        self.fields["password1"].widget.attrs.setdefault("autocomplete", "new-password")
        self.fields["password2"].widget.attrs.setdefault("autocomplete", "new-password")
        apply_control_classes(self.fields)

    def clean_email(self) -> str:
        return validate_unique_email(self.cleaned_data.get("email"))

    def clean_contact_number(self) -> str:
        return validate_contact_number(self.cleaned_data.get("contact_number"))


class CustomAuthenticationForm(AuthenticationForm):
    """Styled login form with explicit credential error messaging."""

    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": (
            "Invalid username or password. Please verify your credentials and try again."
        ),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {"autocomplete": "username", "placeholder": "Enter your username"}
        )
        self.fields["password"].widget.attrs.update(
            {"autocomplete": "current-password", "placeholder": "Enter your password"}
        )
        apply_control_classes(self.fields)


class ProfileUpdateForm(forms.ModelForm):
    """Self-service profile edit form for authenticated users."""

    class Meta:
        model = CustomUser
        fields = (
            "first_name",
            "last_name",
            "email",
            "contact_number",
            "preferred_ferment",
            "bio",
            "profile_photo",
        )
        widgets = {
            "first_name": forms.TextInput(attrs={"autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"autocomplete": "family-name"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "contact_number": forms.TextInput(
                attrs={"autocomplete": "tel", "placeholder": "e.g. +63 917 555 0142"}
            ),
            "preferred_ferment": forms.TextInput(
                attrs={"placeholder": "e.g. Kombucha, Sauerkraut, Hot Sauce"}
            ),
            "bio": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Share what you love to ferment or your jar setup"}
            ),
            "profile_photo": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
        self.fields["email"].required = True
        apply_control_classes(self.fields)

    def clean_email(self) -> str:
        return validate_unique_email(self.cleaned_data.get("email"), exclude_pk=self.instance.pk)

    def clean_contact_number(self) -> str:
        return validate_contact_number(self.cleaned_data.get("contact_number"))
