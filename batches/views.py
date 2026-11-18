from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)

from accounts.models import CustomUser
from dashboard.views import RoleRequiredMixin

from .calculations import calculate_batch_ratios
from .forms import (
    FermentTypeForm,
    JarBatchForm,
    RatioCalculatorForm,
    RatioTemplateForm,
)
from .models import FermentType, JarBatch, RatioTemplate


def _build_active_templates_payload():
    """Return active ratio templates keyed by ID for dynamic client-side previews."""
    templates = RatioTemplate.objects.select_related("ferment_type").filter(
        is_active=True, ferment_type__is_active=True
    )
    return {
        str(tpl.pk): {
            "name": tpl.name,
            "ferment_type_id": str(tpl.ferment_type_id),
            "ferment_type": tpl.ferment_type.name,
            "salt_ratio": str(tpl.salt_ratio) if tpl.salt_ratio is not None else "",
            "sugar_ratio": str(tpl.sugar_ratio) if tpl.sugar_ratio is not None else "",
            "duration": tpl.default_duration_days,
        }
        for tpl in templates
    }


def _parse_decimal_param(raw_value: str | None) -> Decimal | None:
    if not raw_value:
        return None
    try:
        return Decimal(raw_value)
    except (InvalidOperation, TypeError):
        return None


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
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["templates_data"] = _build_active_templates_payload()
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
                selected_capacity=data.get("jar_capacity"),
            )
        )


class FermenterBatchMixin(RoleRequiredMixin):
    """Restrict jar batch inventory management to Home Fermenter accounts."""

    required_role = CustomUser.Role.FERMENTER
    denied_message = (
        "Access denied: Jar batch inventories are reserved for Home Fermenter accounts."
    )


class OwnerBatchMixin(FermenterBatchMixin):
    """Ensure a Home Fermenter can access and mutate only their own jar batches."""

    def get_queryset(self):
        return JarBatch.objects.select_related("ferment_type", "ratio_template", "user")

    def get_object(self, queryset=None):
        obj = super().get_object(queryset=queryset)
        if obj.user_id != self.request.user.id:
            raise PermissionDenied("You can only view and manage your own jar batches.")
        return obj


class BatchListView(FermenterBatchMixin, ListView):
    """Owner-scoped inventory of active, cold storage, completed, and archived batches."""

    model = JarBatch
    template_name = "batches/batch_list.html"
    context_object_name = "batches"

    def get_queryset(self):
        queryset = (
            JarBatch.objects.select_related("ferment_type", "ratio_template")
            .filter(user=self.request.user)
        )
        show_archived = self.request.GET.get("archived") == "1"
        queryset = queryset.filter(is_archived=show_archived)

        status_filter = (self.request.GET.get("status") or "").strip()
        if status_filter in dict(JarBatch.Status.choices):
            queryset = queryset.filter(status=status_filter)

        ferment_type_id = (self.request.GET.get("ferment_type") or "").strip()
        if ferment_type_id.isdigit():
            queryset = queryset.filter(ferment_type_id=int(ferment_type_id))

        search = (self.request.GET.get("q") or "").strip()
        if search:
            queryset = queryset.filter(
                Q(jar_id__icontains=search)
                | Q(batch_name__icontains=search)
                | Q(ferment_type__name__icontains=search)
                | Q(ingredients_notes__icontains=search)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_user_batches = JarBatch.objects.filter(user=self.request.user)
        non_archived = all_user_batches.filter(is_archived=False)
        context["fermenting_count"] = non_archived.filter(
            status=JarBatch.Status.FERMENTING
        ).count()
        context["cold_storage_count"] = non_archived.filter(
            status=JarBatch.Status.COLD_STORAGE
        ).count()
        context["completed_count"] = non_archived.filter(
            status=JarBatch.Status.COMPLETED
        ).count()
        context["archived_count"] = all_user_batches.filter(is_archived=True).count()
        context["ferment_types"] = FermentType.objects.filter(is_active=True)
        context["status_choices"] = JarBatch.Status.choices
        context["show_archived"] = self.request.GET.get("archived") == "1"
        context["selected_status"] = self.request.GET.get("status", "")
        context["selected_ferment_type"] = self.request.GET.get("ferment_type", "")
        context["search_query"] = self.request.GET.get("q", "")
        return context


class BatchCreateView(FermenterBatchMixin, CreateView):
    """Create a new fermentation jar batch owned by the authenticated fermenter."""

    model = JarBatch
    form_class = JarBatchForm
    template_name = "batches/batch_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        tpl_id = self.request.GET.get("template")
        if tpl_id and tpl_id.isdigit():
            tpl = RatioTemplate.objects.filter(pk=int(tpl_id), is_active=True).first()
            if tpl:
                initial["ratio_template"] = tpl
                initial["ferment_type"] = tpl.ferment_type
                initial["salt_ratio"] = tpl.salt_ratio
                initial["sugar_ratio"] = tpl.sugar_ratio
                initial["target_duration_days"] = tpl.default_duration_days

        capacity = _parse_decimal_param(self.request.GET.get("capacity"))
        if capacity and capacity > 0:
            initial["jar_capacity"] = capacity
        salt = _parse_decimal_param(self.request.GET.get("salt"))
        if salt is not None:
            initial["salt_ratio"] = salt
        sugar = _parse_decimal_param(self.request.GET.get("sugar"))
        if sugar is not None:
            initial["sugar_ratio"] = sugar
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["templates_data"] = _build_active_templates_payload()
        return context

    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        messages.success(
            self.request,
            f"Batch '{self.object.jar_id}' has been logged to your fermentation bench.",
        )
        return response

    def form_invalid(self, form):
        messages.error(
            self.request,
            "Could not log your batch. Please fix the highlighted validation errors.",
        )
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse("batch_detail", kwargs={"pk": self.object.pk})


class BatchDetailView(OwnerBatchMixin, DetailView):
    """Detailed view of a jar batch including age counter, ratio math, and notes."""

    model = JarBatch
    template_name = "batches/batch_detail.html"
    context_object_name = "batch"


class BatchUpdateView(OwnerBatchMixin, UpdateView):
    """Owner-scoped update view for modifying jar metadata, ratios, status, and notes."""

    model = JarBatch
    form_class = JarBatchForm
    template_name = "batches/batch_form.html"
    context_object_name = "batch"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["templates_data"] = _build_active_templates_payload()
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f"Batch '{self.object.jar_id}' has been updated.",
        )
        return response

    def form_invalid(self, form):
        messages.error(
            self.request,
            "Could not update your batch. Please fix the highlighted validation errors.",
        )
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse("batch_detail", kwargs={"pk": self.object.pk})


class BatchArchiveToggleView(FermenterBatchMixin, View):
    """Toggle archive state for an owner-scoped jar batch."""

    def post(self, request, pk):
        batch = get_object_or_404(JarBatch, pk=pk)
        if batch.user_id != request.user.id:
            raise PermissionDenied("You can only archive or restore your own jar batches.")
        batch.is_archived = not batch.is_archived
        batch.save(update_fields=["is_archived", "updated_at"])
        state_word = "archived" if batch.is_archived else "restored to active inventory"
        messages.info(request, f"Batch '{batch.jar_id}' was {state_word}.")
        return redirect("batch_detail", pk=batch.pk)


class BatchDeleteView(OwnerBatchMixin, DeleteView):
    """Owner-scoped confirmation and deletion view for a jar batch."""

    model = JarBatch
    template_name = "batches/batch_confirm_delete.html"
    context_object_name = "batch"
    success_url = reverse_lazy("batch_list")

    def form_valid(self, form):
        jar_id = self.object.jar_id
        response = super().form_valid(form)
        messages.success(self.request, f"Batch '{jar_id}' has been permanently deleted.")
        return response


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
