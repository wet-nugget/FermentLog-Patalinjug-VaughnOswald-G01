from django.urls import path

from .views import (
    CustomLoginView,
    CustomLogoutView,
    ProfileOwnershipDetailView,
    ProfileUpdateView,
    SignUpView,
)

urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", CustomLogoutView.as_view(), name="logout"),
    path("profile/", ProfileUpdateView.as_view(), name="profile"),
    path("profile/<int:pk>/", ProfileOwnershipDetailView.as_view(), name="profile_detail"),
]
