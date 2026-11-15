from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser


class RoleDashboardAccessTests(TestCase):
    def setUp(self):
        self.password = "BrineBatch!2026"
        self.fermenter = CustomUser.objects.create_user(
            username="krautkeeper",
            email="kraut@fermentlog.test",
            password=self.password,
            first_name="Kraut",
            last_name="Keeper",
            preferred_ferment="Sauerkraut",
            role=CustomUser.Role.FERMENTER,
        )
        self.admin = CustomUser.objects.create_user(
            username="benchadmin",
            email="admin@fermentlog.test",
            password=self.password,
            first_name="Bench",
            last_name="Admin",
            role=CustomUser.Role.ADMIN,
        )

    def test_anonymous_users_redirect_to_login_from_protected_dashboards(self):
        for route_name in ("dashboard", "fermenter_dashboard", "admin_dashboard", "admin_panel"):
            url = reverse(route_name)
            response = self.client.get(url)
            self.assertRedirects(response, f"{reverse('login')}?next={url}")

    def test_login_routes_each_user_to_role_dashboard(self):
        fermenter_login = self.client.post(
            reverse("login"),
            {"username": "krautkeeper", "password": self.password},
        )
        self.assertRedirects(
            fermenter_login,
            reverse("fermenter_dashboard"),
            fetch_redirect_response=False,
        )

        self.client.post(reverse("logout"))

        admin_login = self.client.post(
            reverse("login"),
            {"username": "benchadmin", "password": self.password},
        )
        self.assertRedirects(
            admin_login,
            reverse("admin_dashboard"),
            fetch_redirect_response=False,
        )

    def test_root_dashboard_redirects_according_to_role(self):
        self.client.force_login(self.fermenter)
        self.assertRedirects(
            self.client.get(reverse("dashboard")),
            reverse("fermenter_dashboard"),
            fetch_redirect_response=False,
        )

        self.client.force_login(self.admin)
        self.assertRedirects(
            self.client.get(reverse("dashboard")),
            reverse("admin_dashboard"),
            fetch_redirect_response=False,
        )

    def test_fermenter_dashboard_content_and_cross_role_block(self):
        self.client.force_login(self.fermenter)

        allowed = self.client.get(reverse("fermenter_dashboard"))
        self.assertEqual(allowed.status_code, 200)
        self.assertContains(allowed, "Fermenter Station")
        self.assertContains(allowed, "Sauerkraut")
        self.assertNotContains(allowed, "Admin Console")

        self.assertEqual(self.client.get(reverse("admin_dashboard")).status_code, 403)
        self.assertEqual(self.client.get(reverse("admin_panel")).status_code, 403)

    def test_admin_dashboard_content_and_cross_role_block(self):
        self.client.force_login(self.admin)

        allowed = self.client.get(reverse("admin_dashboard"))
        self.assertEqual(allowed.status_code, 200)
        self.assertContains(allowed, "Admin Console")
        self.assertContains(allowed, "krautkeeper")
        self.assertNotContains(allowed, "Fermenter Station")

        self.assertEqual(self.client.get(reverse("fermenter_dashboard")).status_code, 403)
