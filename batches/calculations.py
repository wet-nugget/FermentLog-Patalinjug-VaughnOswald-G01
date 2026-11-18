from decimal import Decimal, ROUND_HALF_UP


def _quantize_two(value: Decimal) -> Decimal:
    """Round a Decimal to 2 decimal places using standard half-up rounding."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_batch_ratios(
    *,
    jar_capacity_ml: Decimal,
    headspace_percent: Decimal = Decimal("15.00"),
    produce_weight_g: Decimal | None = None,
    salt_ratio: Decimal | None = None,
    sugar_ratio: Decimal | None = None,
) -> dict[str, Decimal | None]:
    """
    Calculate container working volume, headspace, salt grams, and sugar grams.

    Uses standard 1 mL ≈ 1 g water density for brine and sweet-tea scaling.
    """
    capacity = Decimal(jar_capacity_ml)
    headspace_pct = Decimal(headspace_percent)
    headspace_factor = headspace_pct / Decimal("100")

    headspace_ml = _quantize_two(capacity * headspace_factor)
    working_volume_ml = _quantize_two(capacity - headspace_ml)

    produce_g = Decimal(produce_weight_g) if produce_weight_g else Decimal("0.00")
    total_mass_g = _quantize_two(working_volume_ml + produce_g)

    brine_salt_g = None
    total_salt_g = None
    if salt_ratio is not None:
        salt_factor = Decimal(salt_ratio) / Decimal("100")
        brine_salt_g = _quantize_two(working_volume_ml * salt_factor)
        total_salt_g = _quantize_two(total_mass_g * salt_factor)

    sugar_g = None
    if sugar_ratio is not None:
        sugar_factor = Decimal(sugar_ratio) / Decimal("100")
        sugar_g = _quantize_two(working_volume_ml * sugar_factor)

    return {
        "jar_capacity_ml": _quantize_two(capacity),
        "headspace_percent": _quantize_two(headspace_pct),
        "headspace_ml": headspace_ml,
        "working_volume_ml": working_volume_ml,
        "produce_weight_g": _quantize_two(produce_g),
        "total_mass_g": total_mass_g,
        "brine_salt_g": brine_salt_g,
        "total_salt_g": total_salt_g,
        "sugar_g": sugar_g,
    }
