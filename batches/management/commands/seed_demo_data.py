from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import CustomUser
from batches.models import FermentType, JarBatch, RatioTemplate


class Command(BaseCommand):
    help = "Seed FermentLog demo accounts (admin and fermenter) and sample jar batches."

    def handle(self, *args, **options):
        admin_user, _ = CustomUser.objects.update_or_create(
            username="benchadmin",
            defaults={
                "email": "admin@fermentlog.test",
                "first_name": "Bench",
                "last_name": "Admin",
                "role": CustomUser.Role.ADMIN,
                "is_staff": True,
                "is_active": True,
            },
        )
        admin_user.set_password("BrineAdmin!2026")
        admin_user.save()

        fermenter_user, _ = CustomUser.objects.update_or_create(
            username="krautkeeper",
            defaults={
                "email": "kraut@fermentlog.test",
                "first_name": "Kraut",
                "last_name": "Keeper",
                "preferred_ferment": "Sauerkraut, Kimchi",
                "role": CustomUser.Role.FERMENTER,
                "is_active": True,
            },
        )
        fermenter_user.set_password("BrineBatch!2026")
        fermenter_user.save()

        today = timezone.localdate()
        sauerkraut = FermentType.objects.get(name="Sauerkraut")
        kimchi = FermentType.objects.get(name="Kimchi")
        kombucha = FermentType.objects.get(name="Kombucha")

        kraut_tpl = RatioTemplate.objects.filter(ferment_type=sauerkraut).first()
        kimchi_tpl = RatioTemplate.objects.filter(ferment_type=kimchi).first()
        kombucha_tpl = RatioTemplate.objects.filter(ferment_type=kombucha).first()

        demo_batches = [
            {
                "jar_id": "JAR-01",
                "batch_name": "Autumn Caraway Cabbage Kraut",
                "ferment_type": sauerkraut,
                "ratio_template": kraut_tpl,
                "jar_capacity": Decimal("1000.00"),
                "vessel_material": "Glass Mason Jar",
                "start_date": today - timedelta(days=5),
                "target_duration_days": 21,
                "status": JarBatch.Status.FERMENTING,
                "salt_ratio": Decimal("2.20"),
                "sugar_ratio": None,
                "ingredients_notes": "850g green cabbage, 18.7g sea salt, 1 tsp caraway seeds.",
                "completion_date": None,
            },
            {
                "jar_id": "JAR-02",
                "batch_name": "Gochugaru Napa Kimchi",
                "ferment_type": kimchi,
                "ratio_template": kimchi_tpl,
                "jar_capacity": Decimal("1500.00"),
                "vessel_material": "Ceramic Crock",
                "start_date": today - timedelta(days=12),
                "target_duration_days": 10,
                "status": JarBatch.Status.COLD_STORAGE,
                "salt_ratio": Decimal("2.50"),
                "sugar_ratio": Decimal("1.00"),
                "ingredients_notes": "Napa cabbage, daikon radish, garlic-ginger paste, gochugaru.",
                "completion_date": None,
            },
            {
                "jar_id": "JAR-03",
                "batch_name": "Jasmine Green Tea Kombucha",
                "ferment_type": kombucha,
                "ratio_template": kombucha_tpl,
                "jar_capacity": Decimal("2000.00"),
                "vessel_material": "Wide-Mouth Brew Jar",
                "start_date": today - timedelta(days=14),
                "target_duration_days": 10,
                "status": JarBatch.Status.COMPLETED,
                "salt_ratio": None,
                "sugar_ratio": Decimal("8.00"),
                "ingredients_notes": "Jasmine green tea, organic cane sugar, 200mL starter tea + SCOBY.",
                "completion_date": today - timedelta(days=2),
            },
        ]

        for entry in demo_batches:
            JarBatch.objects.update_or_create(
                user=fermenter_user,
                jar_id=entry["jar_id"],
                defaults=entry,
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded demo accounts (benchadmin, krautkeeper) and 3 sample jar batches."
            )
        )
