from datetime import date, timedelta
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import CustomUser

from .calculations import calculate_batch_ratios
from .models import FermentType, JarBatch, RatioTemplate


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


class JarBatchCrudAndOwnershipTests(TestCase):
    def setUp(self):
        self.password = "BrineBatch!2026"
        self.owner = CustomUser.objects.create_user(
            username="jar_owner",
            email="jar_owner@fermentlog.test",
            password=self.password,
            first_name="Elena",
            last_name="Cruz",
            role=CustomUser.Role.FERMENTER,
        )
        self.other_fermenter = CustomUser.objects.create_user(
            username="other_fermenter",
            email="other_fermenter@fermentlog.test",
            password=self.password,
            first_name="Marco",
            last_name="Tan",
            role=CustomUser.Role.FERMENTER,
        )
        self.admin = CustomUser.objects.create_user(
            username="batch_admin",
            email="batch_admin@fermentlog.test",
            password=self.password,
            first_name="Admin",
            last_name="Steward",
            role=CustomUser.Role.ADMIN,
        )
        self.sauerkraut = FermentType.objects.get(name="Sauerkraut")
        self.kimchi = FermentType.objects.get(name="Kimchi")
        self.kraut_tpl = RatioTemplate.objects.get(name="Classic 2.2% Kraut Brine")

    def test_create_jar_batch_with_template_autofill_and_detail_view(self):
        self.client.force_login(self.owner)
        today = timezone.localdate()
        response = self.client.post(
            reverse("batch_create"),
            {
                "jar_id": "KRAUT-01",
                "batch_name": "Winter Green Kraut",
                "ferment_type": self.sauerkraut.pk,
                "ratio_template": self.kraut_tpl.pk,
                "jar_capacity": "1000.00",
                "vessel_material": "Glass Mason Jar",
                "start_date": (today - timedelta(days=3)).isoformat(),
                "target_duration_days": 21,
                "salt_ratio": "",
                "sugar_ratio": "",
                "status": JarBatch.Status.FERMENTING,
                "completion_date": "",
                "ingredients_notes": "850g cabbage + caraway.",
            },
        )
        batch = JarBatch.objects.get(user=self.owner, jar_id="KRAUT-01")
        self.assertRedirects(response, reverse("batch_detail", kwargs={"pk": batch.pk}))
        self.assertEqual(batch.salt_ratio, Decimal("2.20"))
        self.assertEqual(batch.elapsed_days, 3)

        detail_page = self.client.get(reverse("batch_detail", kwargs={"pk": batch.pk}))
        self.assertEqual(detail_page.status_code, 200)
        self.assertContains(detail_page, "Winter Green Kraut")
        self.assertContains(detail_page, "850.00 mL")
        self.assertContains(detail_page, "18.70 g salt")

    def test_batch_validation_rules_enforced(self):
        self.client.force_login(self.owner)
        JarBatch.objects.create(
            user=self.owner,
            ferment_type=self.sauerkraut,
            jar_id="JAR-DUP",
            jar_capacity=Decimal("1000.00"),
            vessel_material="Glass Mason Jar",
            start_date=date(2026, 11, 1),
            target_duration_days=14,
            status=JarBatch.Status.FERMENTING,
            salt_ratio=Decimal("2.20"),
        )

        # Duplicate jar_id (case-insensitive) for same user + non-positive capacity
        dup_resp = self.client.post(
            reverse("batch_create"),
            {
                "jar_id": "jar-dup",
                "batch_name": "Duplicate Jar",
                "ferment_type": self.sauerkraut.pk,
                "jar_capacity": "0",
                "vessel_material": "Glass Mason Jar",
                "start_date": "2026-11-10",
                "target_duration_days": 14,
                "salt_ratio": "2.20",
                "status": JarBatch.Status.FERMENTING,
            },
        )
        self.assertEqual(dup_resp.status_code, 200)
        form = dup_resp.context["form"]
        self.assertIn("jar_id", form.errors)
        self.assertIn("jar_capacity", form.errors)

        # BR-09: COMPLETED requires completion_date >= start_date
        br09_resp = self.client.post(
            reverse("batch_create"),
            {
                "jar_id": "JAR-NEW",
                "batch_name": "Completed Without Date",
                "ferment_type": self.sauerkraut.pk,
                "jar_capacity": "750",
                "vessel_material": "Glass Mason Jar",
                "start_date": "2026-11-10",
                "target_duration_days": 10,
                "salt_ratio": "2.50",
                "status": JarBatch.Status.COMPLETED,
                "completion_date": "",
            },
        )
        self.assertEqual(br09_resp.status_code, 200)
        self.assertIn("completion_date", br09_resp.context["form"].errors)

        # Mismatched ratio_template for selected ferment_type
        mismatch_resp = self.client.post(
            reverse("batch_create"),
            {
                "jar_id": "JAR-MISMATCH",
                "ferment_type": self.kimchi.pk,
                "ratio_template": self.kraut_tpl.pk,
                "jar_capacity": "1000",
                "vessel_material": "Ceramic Crock",
                "start_date": "2026-11-10",
                "target_duration_days": 10,
                "status": JarBatch.Status.FERMENTING,
            },
        )
        self.assertEqual(mismatch_resp.status_code, 200)
        self.assertIn("ratio_template", mismatch_resp.context["form"].errors)

    def test_update_archive_filter_and_delete_batch(self):
        self.client.force_login(self.owner)
        batch = JarBatch.objects.create(
            user=self.owner,
            ferment_type=self.kimchi,
            jar_id="KIM-07",
            batch_name="Napa Radish Kimchi",
            jar_capacity=Decimal("1500.00"),
            vessel_material="Ceramic Crock",
            start_date=date(2026, 11, 1),
            target_duration_days=10,
            status=JarBatch.Status.FERMENTING,
            salt_ratio=Decimal("2.50"),
        )

        # Update to COMPLETED with completion_date
        edit_resp = self.client.post(
            reverse("batch_edit", kwargs={"pk": batch.pk}),
            {
                "jar_id": "KIM-07",
                "batch_name": "Napa Radish Kimchi Reserve",
                "ferment_type": self.kimchi.pk,
                "jar_capacity": "1500.00",
                "vessel_material": "Ceramic Crock",
                "start_date": "2026-11-01",
                "target_duration_days": 10,
                "salt_ratio": "2.50",
                "sugar_ratio": "1.00",
                "status": JarBatch.Status.COMPLETED,
                "completion_date": "2026-11-12",
                "ingredients_notes": "Tangy and crisp after 11 days.",
            },
        )
        self.assertRedirects(edit_resp, reverse("batch_detail", kwargs={"pk": batch.pk}))
        batch.refresh_from_db()
        self.assertEqual(batch.status, JarBatch.Status.COMPLETED)
        self.assertEqual(batch.batch_name, "Napa Radish Kimchi Reserve")

        # Search and filter on batch_list
        filtered = self.client.get(reverse("batch_list"), {"q": "Reserve", "status": "COMPLETED"})
        self.assertContains(filtered, "KIM-07")

        # Archive toggle hides from active list and shows in archived view
        arch_resp = self.client.post(reverse("batch_archive_toggle", kwargs={"pk": batch.pk}))
        self.assertRedirects(arch_resp, reverse("batch_detail", kwargs={"pk": batch.pk}))
        batch.refresh_from_db()
        self.assertTrue(batch.is_archived)
        self.assertNotContains(self.client.get(reverse("batch_list")), "KIM-07")
        self.assertContains(self.client.get(reverse("batch_list"), {"archived": "1"}), "KIM-07")

        # Delete permanently
        del_resp = self.client.post(reverse("batch_delete", kwargs={"pk": batch.pk}))
        self.assertRedirects(del_resp, reverse("batch_list"))
        self.assertFalse(JarBatch.objects.filter(pk=batch.pk).exists())

    def test_owner_isolation_and_role_restriction(self):
        batch = JarBatch.objects.create(
            user=self.owner,
            ferment_type=self.sauerkraut,
            jar_id="PRIV-01",
            jar_capacity=Decimal("1000.00"),
            vessel_material="Glass Mason Jar",
            start_date=date(2026, 11, 5),
            target_duration_days=14,
            status=JarBatch.Status.FERMENTING,
            salt_ratio=Decimal("2.20"),
        )

        # Another fermenter cannot see it in list or access detail/edit/archive/delete
        self.client.force_login(self.other_fermenter)
        list_page = self.client.get(reverse("batch_list"))
        self.assertNotContains(list_page, "PRIV-01")
        self.assertEqual(self.client.get(reverse("batch_detail", kwargs={"pk": batch.pk})).status_code, 403)
        self.assertEqual(self.client.get(reverse("batch_edit", kwargs={"pk": batch.pk})).status_code, 403)
        self.assertEqual(self.client.post(reverse("batch_archive_toggle", kwargs={"pk": batch.pk})).status_code, 403)
        self.assertEqual(self.client.get(reverse("batch_delete", kwargs={"pk": batch.pk})).status_code, 403)

        # Admin cannot access fermenter batch logger pages
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("batch_list")).status_code, 403)
        self.assertEqual(self.client.get(reverse("batch_create")).status_code, 403)

    def test_seed_demo_data_command_creates_accounts_and_batches(self):
        call_command("seed_demo_data")
        admin_user = CustomUser.objects.get(username="benchadmin")
        fermenter_user = CustomUser.objects.get(username="krautkeeper")
        self.assertEqual(admin_user.role, CustomUser.Role.ADMIN)
        self.assertEqual(fermenter_user.role, CustomUser.Role.FERMENTER)
        self.assertEqual(JarBatch.objects.filter(user=fermenter_user).count(), 3)
