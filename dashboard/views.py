from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.views.generic import RedirectView, TemplateView

from accounts.models import CustomUser
from accounts.views import get_role_dashboard_url

STANDARD_CULTURES = [
    {
        "name": "Sauerkraut",
        "ratio": "2.0%–2.5% salt",
        "cadence": "Daily burp · 14–28d",
        "vessel": "Glass mason jar",
    },
    {
        "name": "Kimchi",
        "ratio": "2.5% salt",
        "cadence": "Daily burp · 5–14d",
        "vessel": "Glass crock / jar",
    },
    {
        "name": "Hot Sauce",
        "ratio": "3.0%–3.5% brine",
        "cadence": "Daily check · 14–21d",
        "vessel": "Airlock glass jar",
    },
    {
        "name": "Kombucha",
        "ratio": "7%–10% sugar",
        "cadence": "Culture feed · 7–14d",
        "vessel": "Wide-mouth brew jar",
    },
]

REFERENCE_CATEGORIES = [
    {
        "entity": "ferment_types",
        "label": "Standard Ferment Categories",
        "scope": "Kombucha, Sauerkraut, Kimchi, Hot Sauce",
        "phase": "Phase 3 Ready",
    },
    {
        "entity": "ratio_templates",
        "label": "Brine & Sugar Ratio Templates",
        "scope": "Default salt % and sugar % presets per ferment type",
        "phase": "Phase 3 Ready",
    },
    {
        "entity": "users",
        "label": "Role & Access Registry",
        "scope": "FERMENTER and ADMINISTRATOR role boundaries",
        "phase": "Active in Phase 1",
    },
]


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
    """Home Fermenter station dashboard."""

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
        context["fermenter_count"] = CustomUser.objects.filter(
            role=CustomUser.Role.FERMENTER
        ).count()
        context["standard_cultures"] = STANDARD_CULTURES
        context["profile_fields_completed"] = completed_count
        context["profile_fields_total"] = len(tracked_fields)
        context["profile_completion_percent"] = round(
            (completed_count / len(tracked_fields)) * 100
        )
        return context


class AdminDashboardView(RoleRequiredMixin, TemplateView):
    """Administrator console for user oversight and role governance."""

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
        context["recent_users"] = CustomUser.objects.order_by("-date_joined")[:20]
        context["reference_categories"] = REFERENCE_CATEGORIES
        return context
