import logging


def format_routine_markdown(
    routine: dict, user_preferred_units: str = "imperial"
) -> str:
    """Format a workout routine in a readable markdown format.

    Args:
        routine: The routine dictionary from the API response
        user_preferred_units: User's preferred unit system ("imperial" or "metric")

    Returns:
        Formatted markdown string
    """
    logger = logging.getLogger(__name__)

    # Import unit conversion functions
    from app.utils.units import convert_weight_for_display, get_weight_unit_label

    # Get weight unit label for display
    weight_unit = get_weight_unit_label(user_preferred_units)

    # Log the keys present in the routine data
    logger.info(f"Routine data keys: {list(routine.keys())}")

    if not routine or "hevy_api" not in routine or "routine" not in routine["hevy_api"]:
        return "Invalid routine format"

    routine_data = routine["hevy_api"]["routine"]

    # Start with the routine name and description
    routine_name = (
        routine_data.get("name") or routine_data.get("title") or "Untitled Routine"
    )
    markdown = f"## {routine_name}\n\n"
    if "notes" in routine_data and routine_data["notes"]:
        markdown += f"*{routine_data['notes']}*\n\n"

    # Add each exercise
    for exercise in routine_data.get("exercises", []):
        logger.info(f"Exercise keys: {list(exercise.keys())}")
        exercise_name = (
            exercise.get("name") or exercise.get("title") or "Unknown Exercise"
        )
        markdown += f"### {exercise_name}\n"

        # Add exercise description if available
        if "exercise_description" in exercise and exercise["exercise_description"]:
            markdown += f"{exercise['exercise_description']}\n\n"

        # Add exercise notes if available
        if "notes" in exercise and exercise["notes"]:
            markdown += f"*{exercise['notes']}*\n\n"

        # Add sets
        markdown += "**Sets:**\n"
        for i, set_data in enumerate(exercise.get("sets", []), 1):
            set_type = set_data.get("type", "normal").capitalize()
            reps = set_data.get("reps", "N/A")

            # Convert weight to user's preferred units for display
            weight_kg = set_data.get("weight_kg")
            if weight_kg is not None and weight_kg > 0:
                display_weight = convert_weight_for_display(
                    weight_kg, user_preferred_units
                )
                weight = f"{display_weight:.1f}{weight_unit}"
            elif weight_kg == 0:
                weight = "Bodyweight"
            else:
                weight = "N/A"

            duration = (
                f"{set_data.get('duration_seconds', 'N/A')}s"
                if set_data.get("duration_seconds")
                else ""
            )

            set_info = []
            if reps != "N/A":
                set_info.append(f"{reps} reps")
            if weight != "N/A":
                set_info.append(weight)
            if duration:
                set_info.append(duration)

            markdown += f"{i}. {set_type}: {', '.join(set_info)}\n"

        # Add rest time if specified
        if "rest_seconds" in exercise and exercise["rest_seconds"]:
            markdown += f"*Rest: {exercise['rest_seconds']} seconds*\n\n"
        else:
            markdown += "\n"

    return markdown
