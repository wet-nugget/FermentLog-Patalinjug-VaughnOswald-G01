from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.views.generic import RedirectView, TemplateView

from accounts.models import CustomUser
from accounts.views import get_role_dashboard_url
from batches.models import FermentType, JarBatch, RatioTemplate


class RoleRequiredMixin(LoginRequiredMixin):
    """Redirect unauthenticated visitors to login and block cross-role access with 403."""

    required_role = None
    denied_message = "You do not have permission to access this dashboard."

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if self.required_role and request.user.role != self.required_role:
            raise PermissionDenied(self.denied_message)
        return super().dispatch(request, *args, **kwargs)


class DashboardRedirectView(LoginRequiredMixin, RedirectView):
    """Route authenticated users to the dashboard matching their role."""

    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        return get_role_dashboard_url(self.request.user)


class FermenterDashboardView(RoleRequiredMixin, TemplateView):
    """Home Fermenter station dashboard showing active jars and culture baselines."""

    required_role = CustomUser.Role.FERMENTER
    denied_message = (
        "Access denied: The Home Fermenter station is reserved for Home Fermenter accounts."
    )
    template_name = "dashboard/fermenter_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        tracked_fields = [
            user.first_name,
            user.last_name,
            user.email,
            user.contact_number,
            user.preferred_ferment,
            user.bio,
        ]
        completed_count = sum(1 for value in tracked_fields if bool(value))

        user_batches = JarBatch.objects.select_related(
            "ferment_type", "ratio_template"
        ).filter(user=user, is_archived=False)
        active_batches = user_batches.filter(
            status__in=[JarBatch.Status.FERMENTING, JarBatch.Status.COLD_STORAGE]
        )

        context["active_batches"] = active_batches[:6]
        context["active_batch_count"] = user_batches.filter(
            status=JarBatch.Status.FERMENTING
        ).count()
        context["cold_storage_count"] = user_batches.filter(
            status=JarBatch.Status.COLD_STORAGE
        ).count()
        context["completed_batch_count"] = user_batches.filter(
            status=JarBatch.Status.COMPLETED
        ).count()
        context["standard_cultures"] = FermentType.objects.prefetch_related(
            "ratio_templates"
        ).filter(is_active=True)
        context["profile_fields_completed"] = completed_count
        context["profile_fields_total"] = len(tracked_fields)
        context["profile_completion_percent"] = round(
            (completed_count / len(tracked_fields)) * 100
        )
        return context


class AdminDashboardView(RoleRequiredMixin, TemplateView):
    """Administrator console for user oversight and standard reference data."""

    required_role = CustomUser.Role.ADMIN
    denied_message = (
        "Access denied: This console is restricted to Administrator accounts."
    )
    template_name = "dashboard/admin_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_users"] = CustomUser.objects.count()
        context["fermenter_count"] = CustomUser.objects.filter(
            role=CustomUser.Role.FERMENTER
        ).count()
        context["admin_count"] = CustomUser.objects.filter(
            role=CustomUser.Role.ADMIN
        ).count()
        context["ferment_type_count"] = FermentType.objects.filter(is_active=True).count()
        context["ratio_template_count"] = RatioTemplate.objects.filter(
            is_active=True
        ).count()
        context["total_batch_count"] = JarBatch.objects.count()
        context["recent_users"] = CustomUser.objects.order_by("-date_joined")[:20]
        context["reference_categories"] = [
            {
                "label": "Standard Ferment Categories",
                "count": FermentType.objects.count(),
                "scope": "Kombucha, Sauerkraut, Kimchi, Hot Sauce, and custom baselines",
                "status": "Active",
            },
            {
                "label": "Brine & Sugar Ratio Templates",
                "count": RatioTemplate.objects.count(),
                "scope": "Salt % and sugar % presets used by the Batch & Jar Logger",
                "status": "Active",
            },
            {
                "label": "Logged Jar Batches",
                "count": JarBatch.objects.count(),
                "scope": "Owner-scoped fermentation vessels tracked across all members",
                "status": "Active",
            },
        ]
        return context
