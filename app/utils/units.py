def inches_to_cm(inches: float) -> float:
    """Convert inches to centimeters."""
    return inches * 2.54


def lbs_to_kg(lbs: float) -> float:
    """Convert pounds to kilograms."""
    return lbs * 0.45359237


def cm_to_inches(cm: float) -> float:
    """Convert centimeters to inches."""
    return cm / 2.54


def kg_to_lbs(kg: float) -> float:
    """Convert kilograms to pounds."""
    return kg / 0.45359237


def format_height_cm(cm: float) -> str:
    """Format height in centimeters as feet and inches."""
    inches = cm_to_inches(cm)
    feet = int(inches // 12)
    remaining_inches = round(inches % 12, 1)
    return f"{feet}'{remaining_inches}\""


def format_weight_kg(kg: float) -> str:
    """Format weight in kilograms as pounds."""
    return f"{round(kg_to_lbs(kg), 1)} lbs"


def convert_weight_for_display(weight_kg: float, unit_system: str) -> float:
    """Convert weight from kg (database format) to user's preferred units."""
    if unit_system == "imperial":
        return kg_to_lbs(weight_kg)
    return weight_kg


def convert_weight_from_display(weight_value: float, unit_system: str) -> float:
    """Convert weight from user's preferred units to kg (database format)."""
    if unit_system == "imperial":
        return lbs_to_kg(weight_value)
    return weight_value


def get_weight_unit_label(unit_system: str) -> str:
    """Get the weight unit label for display."""
    return "lbs" if unit_system == "imperial" else "kg"


def convert_height_for_display(height_cm: float, unit_system: str) -> tuple:
    """Convert height from cm (database format) to user's preferred units.

    Returns:
        For imperial: (feet, inches)
        For metric: (cm, 0) - second value is always 0 for consistency
    """
    if unit_system == "imperial":
        inches_total = cm_to_inches(height_cm)
        feet = int(inches_total // 12)
        inches = int(inches_total % 12)
        return (feet, inches)
    return (int(height_cm), 0)


def get_height_unit_labels(unit_system: str) -> tuple:
    """Get the height unit labels for display.

    Returns:
        For imperial: ("feet", "inches")
        For metric: ("cm", "") - second label is empty
    """
    if unit_system == "imperial":
        return ("feet", "inches")
    return ("cm", "")


def round_weight_to_practical_imperial(weight_kg: float) -> float:
    """
    Round a weight in kg to a value that converts to a practical 5-lb increment.

    Args:
        weight_kg: Weight in kilograms

    Returns:
        Weight in kg that converts to a 5-lb increment
    """
    # Convert to lbs, round to nearest 5, then convert back to kg
    weight_lbs = kg_to_lbs(weight_kg)
    rounded_lbs = round(weight_lbs / 5) * 5
    return lbs_to_kg(rounded_lbs)


def get_practical_imperial_weights_kg() -> dict:
    """
    Get a mapping of practical imperial weights (5-lb increments) to their kg equivalents.

    Returns:
        Dictionary mapping lb values to kg values
    """
    practical_weights = {}
    for lbs in range(5, 201, 5):  # 5 lbs to 200 lbs in 5-lb increments
        kg = lbs_to_kg(lbs)
        practical_weights[lbs] = round(kg, 1)
    return practical_weights


def suggest_practical_weight_kg(
    target_weight_kg: float, preferred_units: str = "imperial"
) -> float:
    """
    Suggest a practical weight in kg based on user's preferred units.

    For imperial users, rounds to weights that convert to 5-lb increments.
    For metric users, rounds to 2.5kg increments (standard gym increments).

    Args:
        target_weight_kg: Target weight in kg
        preferred_units: User's preferred unit system

    Returns:
        Practical weight in kg
    """
    if preferred_units == "imperial":
        return round_weight_to_practical_imperial(target_weight_kg)
    else:
        # For metric users, round to nearest 2.5kg (common gym increment)
        return round(target_weight_kg / 2.5) * 2.5
