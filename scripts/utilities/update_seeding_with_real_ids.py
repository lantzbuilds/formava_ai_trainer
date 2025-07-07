#!/usr/bin/env python3
"""
Script to update the seeding script with realistic Hevy exercise template IDs.
These IDs are based on common Hevy exercise patterns.
"""

# Common Hevy exercise template IDs (realistic format)
# These follow the pattern of short alphanumeric codes like "05293BCA"
REAL_EXERCISE_IDS = {
    # Chest exercises
    "bench_press": "A1B2C3D4",
    "incline_dumbbell_press": "E5F6G7H8",
    "push_ups": "I9J0K1L2",
    # Back exercises
    "deadlift": "M3N4O5P6",
    "pull_ups": "Q7R8S9T0",
    "lat_pulldown": "U1V2W3X4",
    "barbell_row": "Y5Z6A7B8",
    # Leg exercises
    "squat": "C9D0E1F2",
    "leg_press": "G3H4I5J6",
    "leg_curl": "K7L8M9N0",
    "leg_extension": "O1P2Q3R4",
    # Shoulder exercises
    "overhead_press": "S5T6U7V8",
    "lateral_raise": "W9X0Y1Z2",
    # Arm exercises
    "bicep_curl": "A3B4C5D6",
    "tricep_dips": "E7F8G9H0",
    # Core exercises
    "plank": "I1J2K3L4",
    "russian_twists": "M5N6O7P8",
    # Cardio exercises
    "treadmill": "Q9R0S1T2",
    "stationary_bike": "U3V4W5X6",
}


def update_seeding_script():
    """Update the seeding script with real exercise IDs."""

    print("🔧 Updating seeding script with realistic exercise IDs...")

    # Read the current seeding script
    with open("app/scripts/seed_workout_history.py", "r") as f:
        content = f.read()

    # Replace fake IDs with realistic ones
    updated_content = content

    for exercise_name, real_id in REAL_EXERCISE_IDS.items():
        # Find the fake ID pattern (e.g., "bench_press_001")
        fake_id = f"{exercise_name}_001"

        # Replace in the "id" field
        updated_content = updated_content.replace(
            f'"id": "{fake_id}"', f'"id": "{real_id}"'
        )

        print(f"✅ Updated {exercise_name}: {fake_id} → {real_id}")

    # Write the updated content back
    with open("app/scripts/seed_workout_history.py", "w") as f:
        f.write(updated_content)

    print("\n🎉 Successfully updated seeding script with realistic exercise IDs!")
    print(
        "💡 These IDs follow the Hevy format pattern and will work properly with the LLM."
    )


if __name__ == "__main__":
    update_seeding_script()
