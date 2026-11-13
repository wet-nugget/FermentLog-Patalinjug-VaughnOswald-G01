from django.urls import path

from .views import AdminDashboardView, DashboardRedirectView, FermenterDashboardView

urlpatterns = [
    path("", DashboardRedirectView.as_view(), name="dashboard"),
    path("dashboard/fermenter/", FermenterDashboardView.as_view(), name="fermenter_dashboard"),
    path("dashboard/admin/", AdminDashboardView.as_view(), name="admin_dashboard"),
    path("admin-panel/", AdminDashboardView.as_view(), name="admin_panel"),
]
