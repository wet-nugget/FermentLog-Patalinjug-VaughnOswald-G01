from decimal import Decimal

from django.db import migrations

SEED_FERMENT_TYPES = [
    {
        "name": "Sauerkraut",
        "description": "Lacto-fermented shredded cabbage preserved in its own salt brine.",
        "default_cadence": "Daily burp · 14–28d",
        "recommended_vessel": "Glass mason jar",
        "templates": [
            {
                "name": "Classic 2.2% Kraut Brine",
                "salt_ratio": Decimal("2.20"),
                "sugar_ratio": None,
                "default_duration_days": 21,
            }
        ],
    },
    {
        "name": "Kimchi",
        "description": "Spiced napa cabbage and radish lacto-ferment with aromatic paste.",
        "default_cadence": "Daily burp · 5–14d",
        "recommended_vessel": "Glass crock / jar",
        "templates": [
            {
                "name": "Traditional 2.5% Kimchi Brine",
                "salt_ratio": Decimal("2.50"),
                "sugar_ratio": Decimal("1.00"),
                "default_duration_days": 10,
            }
        ],
    },
    {
        "name": "Hot Sauce",
        "description": "Lacto-fermented chili pepper mash or whole-pod salt brine.",
        "default_cadence": "Daily check · 14–21d",
        "recommended_vessel": "Airlock glass jar",
        "templates": [
            {
                "name": "3.5% Pepper Mash Brine",
                "salt_ratio": Decimal("3.50"),
                "sugar_ratio": None,
                "default_duration_days": 14,
            }
        ],
    },
    {
        "name": "Kombucha",
        "description": "Sweetened black or green tea fermented by a symbiotic culture (SCOBY).",
        "default_cadence": "Culture feed · 7–14d",
        "recommended_vessel": "Wide-mouth brew jar",
        "templates": [
            {
                "name": "8.0% Sweet Tea Kombucha Base",
                "salt_ratio": None,
                "sugar_ratio": Decimal("8.00"),
                "default_duration_days": 10,
            }
        ],
    },
]


def seed_reference_data(apps, schema_editor):
    FermentType = apps.get_model("batches", "FermentType")
    RatioTemplate = apps.get_model("batches", "RatioTemplate")

    for entry in SEED_FERMENT_TYPES:
        ferment_type, _ = FermentType.objects.get_or_create(
            name=entry["name"],
            defaults={
                "description": entry["description"],
                "default_cadence": entry["default_cadence"],
                "recommended_vessel": entry["recommended_vessel"],
                "is_active": True,
            },
        )
        for tpl in entry["templates"]:
            RatioTemplate.objects.get_or_create(
                ferment_type=ferment_type,
                name=tpl["name"],
                defaults={
                    "salt_ratio": tpl["salt_ratio"],
                    "sugar_ratio": tpl["sugar_ratio"],
                    "default_duration_days": tpl["default_duration_days"],
                    "is_active": True,
                },
            )


def reverse_seed_reference_data(apps, schema_editor):
    FermentType = apps.get_model("batches", "FermentType")
    FermentType.objects.filter(
        name__in=[entry["name"] for entry in SEED_FERMENT_TYPES]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("batches", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_reference_data, reverse_seed_reference_data),
    ]
