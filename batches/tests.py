from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser

from .calculations import calculate_batch_ratios
from .models import FermentType, RatioTemplate


class RatioCalculatorTests(TestCase):
    def setUp(self):
        self.fermenter = CustomUser.objects.create_user(
            username="krautcalc",
            email="calc@fermentlog.test",
            password="BrineBatch!2026",
            first_name="Calc",
            last_name="User",
            role=CustomUser.Role.FERMENTER,
        )

    def test_ratio_math_with_headspace_and_produce_weight(self):
        result = calculate_batch_ratios(
            jar_capacity_ml=Decimal("1000.00"),
            headspace_percent=Decimal("15.00"),
            produce_weight_g=Decimal("400.00"),
            salt_ratio=Decimal("2.50"),
            sugar_ratio=Decimal("8.00"),
        )
        self.assertEqual(result["headspace_ml"], Decimal("150.00"))
        self.assertEqual(result["working_volume_ml"], Decimal("850.00"))
        self.assertEqual(result["total_mass_g"], Decimal("1250.00"))
        self.assertEqual(result["brine_salt_g"], Decimal("21.25"))
        self.assertEqual(result["total_salt_g"], Decimal("31.25"))
        self.assertEqual(result["sugar_g"], Decimal("68.00"))

    def test_calculator_view_requires_salt_or_sugar_ratio(self):
        self.client.force_login(self.fermenter)
        response = self.client.post(
            reverse("ratio_calculator"),
            {
                "jar_capacity": "1000.00",
                "headspace_percent": "15.00",
                "produce_weight_g": "0.00",
                "salt_ratio": "",
                "sugar_ratio": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].non_field_errors())

    def test_calculator_view_loads_template_and_computes_output(self):
        self.client.force_login(self.fermenter)
        tpl = RatioTemplate.objects.get(name="Classic 2.2% Kraut Brine")
        response = self.client.post(
            reverse("ratio_calculator"),
            {
                "ratio_template": tpl.pk,
                "jar_capacity": "2000.00",
                "headspace_percent": "15.00",
                "produce_weight_g": "0.00",
                "salt_ratio": "",
                "sugar_ratio": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1700.00 mL")
        self.assertContains(response, "37.40 g")


class AdminReferenceLibraryTests(TestCase):
    def setUp(self):
        self.fermenter = CustomUser.objects.create_user(
            username="regularfermenter",
            email="fermenter@fermentlog.test",
            password="BrineBatch!2026",
            first_name="Regular",
            last_name="Fermenter",
            role=CustomUser.Role.FERMENTER,
        )
        self.admin = CustomUser.objects.create_user(
            username="libraryadmin",
            email="libadmin@fermentlog.test",
            password="BrineAdmin!2026",
            first_name="Library",
            last_name="Admin",
            role=CustomUser.Role.ADMIN,
        )

    def test_seeded_reference_data_exists(self):
        self.assertGreaterEqual(FermentType.objects.count(), 4)
        self.assertGreaterEqual(RatioTemplate.objects.count(), 4)

    def test_fermenter_cannot_manage_reference_library(self):
        self.client.force_login(self.fermenter)
        for route in ("reference_library", "ferment_type_create", "ratio_template_create"):
            self.assertEqual(self.client.get(reverse(route)).status_code, 403)

    def test_admin_can_create_ferment_type_and_ratio_template(self):
        self.client.force_login(self.admin)
        cat_resp = self.client.post(
            reverse("ferment_type_create"),
            {
                "name": "Miso",
                "description": "Soybean and koji salt-aged paste.",
                "default_cadence": "Monthly weight check · 90–180d",
                "recommended_vessel": "Ceramic crock",
                "is_active": True,
            },
        )
        self.assertRedirects(cat_resp, reverse("reference_library"))
        miso = FermentType.objects.get(name="Miso")

        tpl_resp = self.client.post(
            reverse("ratio_template_create"),
            {
                "ferment_type": miso.pk,
                "name": "12% Sweet White Miso",
                "salt_ratio": "12.00",
                "sugar_ratio": "",
                "default_duration_days": 90,
                "is_active": True,
            },
        )
        self.assertRedirects(tpl_resp, reverse("reference_library"))
        self.assertTrue(
            RatioTemplate.objects.filter(ferment_type=miso, name="12% Sweet White Miso").exists()
        )
