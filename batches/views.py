from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, FormView, TemplateView, UpdateView

from accounts.models import CustomUser
from dashboard.views import RoleRequiredMixin

from .calculations import calculate_batch_ratios
from .forms import FermentTypeForm, RatioCalculatorForm, RatioTemplateForm
from .models import FermentType, RatioTemplate


class RatioCalculatorView(LoginRequiredMixin, FormView):
    """Recipe & Ratio Calculator computing container working volume, salt, and sugar grams."""

    template_name = "batches/calculator.html"
    form_class = RatioCalculatorForm

    def get_initial(self):
        initial = super().get_initial()
        template_id = self.request.GET.get("template")
        if template_id and template_id.isdigit():
            template = (
                RatioTemplate.objects.select_related("ferment_type")
                .filter(pk=int(template_id), is_active=True)
                .first()
            )
            if template:
                initial["ratio_template"] = template
                initial["salt_ratio"] = template.salt_ratio
                initial["sugar_ratio"] = template.sugar_ratio
                initial["default_duration_days"] = template.default_duration_days
        return initial

    def _build_template_payload(self):
        templates = RatioTemplate.objects.select_related("ferment_type").filter(
            is_active=True, ferment_type__is_active=True
        )
        return {
            str(tpl.pk): {
                "name": tpl.name,
                "ferment_type": tpl.ferment_type.name,
                "salt_ratio": str(tpl.salt_ratio) if tpl.salt_ratio is not None else "",
                "sugar_ratio": str(tpl.sugar_ratio) if tpl.sugar_ratio is not None else "",
                "duration": tpl.default_duration_days,
            }
            for tpl in templates
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["templates_data"] = self._build_template_payload()
        if "calculation" not in context:
            initial = self.get_initial()
            salt_val = initial.get("salt_ratio")
            sugar_val = initial.get("sugar_ratio")
            if salt_val is None and sugar_val is None:
                salt_val = Decimal("2.20")
            context["calculation"] = calculate_batch_ratios(
                jar_capacity_ml=initial.get("jar_capacity", Decimal("1000.00")),
                headspace_percent=initial.get("headspace_percent", Decimal("15.00")),
                produce_weight_g=initial.get("produce_weight_g", Decimal("0.00")),
                salt_ratio=salt_val,
                sugar_ratio=sugar_val,
            )
            context["selected_salt_ratio"] = salt_val
            context["selected_sugar_ratio"] = sugar_val
        return context

    def form_valid(self, form):
        data = form.cleaned_data
        calculation = calculate_batch_ratios(
            jar_capacity_ml=data["jar_capacity"],
            headspace_percent=data["headspace_percent"],
            produce_weight_g=data.get("produce_weight_g"),
            salt_ratio=data.get("salt_ratio"),
            sugar_ratio=data.get("sugar_ratio"),
        )
        return self.render_to_response(
            self.get_context_data(
                form=form,
                calculation=calculation,
                selected_template=data.get("ratio_template"),
                selected_salt_ratio=data.get("salt_ratio"),
                selected_sugar_ratio=data.get("sugar_ratio"),
            )
        )


class AdminReferenceMixin(RoleRequiredMixin):
    """Restrict reference category and ratio template writes to Administrator accounts."""

    required_role = CustomUser.Role.ADMIN
    denied_message = (
        "Access denied: Standard ferment categories and ratio templates can only be managed by Administrators."
    )


class ReferenceLibraryView(AdminReferenceMixin, TemplateView):
    """Administrator catalog view of FermentTypes and RatioTemplates."""

    template_name = "batches/reference_library.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ferment_types"] = FermentType.objects.prefetch_related(
            "ratio_templates"
        ).all()
        context["ratio_templates"] = RatioTemplate.objects.select_related(
            "ferment_type"
        ).all()
        return context


class FermentTypeCreateView(AdminReferenceMixin, SuccessMessageMixin, CreateView):
    """Create a new standard ferment category (Administrator only)."""

    model = FermentType
    form_class = FermentTypeForm
    template_name = "batches/ferment_type_form.html"
    success_url = reverse_lazy("reference_library")
    success_message = "Ferment category '%(name)s' has been added to the reference library."

    def form_invalid(self, form):
        messages.error(
            self.request,
            "Could not save the ferment category. Please check the errors below.",
        )
        return super().form_invalid(form)


class FermentTypeUpdateView(AdminReferenceMixin, SuccessMessageMixin, UpdateView):
    """Edit an existing standard ferment category (Administrator only)."""

    model = FermentType
    form_class = FermentTypeForm
    template_name = "batches/ferment_type_form.html"
    success_url = reverse_lazy("reference_library")
    success_message = "Ferment category '%(name)s' has been updated."

    def form_invalid(self, form):
        messages.error(
            self.request,
            "Could not update the ferment category. Please check the errors below.",
        )
        return super().form_invalid(form)


class RatioTemplateCreateView(AdminReferenceMixin, SuccessMessageMixin, CreateView):
    """Create a new ratio template preset (Administrator only)."""

    model = RatioTemplate
    form_class = RatioTemplateForm
    template_name = "batches/ratio_template_form.html"
    success_url = reverse_lazy("reference_library")
    success_message = "Ratio template '%(name)s' has been created."

    def form_invalid(self, form):
        messages.error(
            self.request,
            "Could not save the ratio template. Please check the errors below.",
        )
        return super().form_invalid(form)


class RatioTemplateUpdateView(AdminReferenceMixin, SuccessMessageMixin, UpdateView):
    """Edit an existing ratio template preset (Administrator only)."""

    model = RatioTemplate
    form_class = RatioTemplateForm
    template_name = "batches/ratio_template_form.html"
    success_url = reverse_lazy("reference_library")
    success_message = "Ratio template '%(name)s' has been updated."

    def form_invalid(self, form):
        messages.error(
            self.request,
            "Could not update the ratio template. Please check the errors below.",
        )
        return super().form_invalid(form)
