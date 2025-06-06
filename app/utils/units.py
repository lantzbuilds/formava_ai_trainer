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
