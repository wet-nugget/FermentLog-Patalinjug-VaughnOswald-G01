from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, UpdateView

from .forms import CustomAuthenticationForm, CustomUserCreationForm, ProfileUpdateForm
from .models import CustomUser


def get_role_dashboard_url(user: CustomUser) -> str:
    """Return the landing dashboard URL corresponding to the user's role."""
    if user.role == CustomUser.Role.ADMIN:
        return reverse("admin_dashboard")
    return reverse("fermenter_dashboard")


class SignUpView(CreateView):
    """Account registration view creating hashed Django user accounts."""

    form_class = CustomUserCreationForm
    template_name = "registration/signup.html"
    success_url = reverse_lazy("login")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(get_role_dashboard_url(request.user))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            "Your FermentLog account is ready. Sign in to start tracking your batches and jars.",
        )
        return response

    def form_invalid(self, form):
        messages.error(
            self.request,
            "Please correct the highlighted errors below to complete registration.",
        )
        return super().form_invalid(form)


class CustomLoginView(LoginView):
    """Session login view routing each user to their role-specific dashboard."""

    form_class = CustomAuthenticationForm
    template_name = "registration/login.html"
    redirect_authenticated_user = True

    def get_success_url(self) -> str:
        redirect_to = self.get_redirect_url()
        if redirect_to:
            return redirect_to
        return get_role_dashboard_url(self.request.user)

    def form_valid(self, form):
        response = super().form_valid(form)
        user = form.get_user()
        messages.success(
            self.request,
            f"Welcome back, {user.first_name or user.username}.",
        )
        return response

    def form_invalid(self, form):
        messages.error(
            self.request,
            "Invalid username or password. Please check your credentials and try again.",
        )
        return super().form_invalid(form)


class CustomLogoutView(LogoutView):
    """Ends the user's authenticated session and returns to sign in."""

    next_page = reverse_lazy("login")

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        messages.info(request, "You have signed out of your FermentLog session.")
        return response


class ProfileUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Allows logged-in users to view and update only their own profile."""

    model = CustomUser
    form_class = ProfileUpdateForm
    template_name = "accounts/profile_form.html"
    success_url = reverse_lazy("profile")
    success_message = "Your profile has been updated."

    def get_object(self, queryset=None):
        return self.request.user

    def form_invalid(self, form):
        messages.error(
            self.request,
            "Could not update your profile. Please check the errors below.",
        )
        return super().form_invalid(form)


class ProfileOwnershipDetailView(LoginRequiredMixin, View):
    """Enforces self-only access when a user navigates to a profile ID URL."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if kwargs.get("pk") != request.user.pk:
            raise PermissionDenied("You can only view and edit your own profile.")
        return redirect("profile")
