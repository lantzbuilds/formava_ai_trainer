#!/usr/bin/env python3
"""
Script to fetch real exercise template IDs from the Hevy API.
This will give us the actual exercise IDs to use in the seeding script.
"""
import json
import os
import sys
from collections import defaultdict

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.hevy_api import HevyAPI


def fetch_hevy_exercise_ids():
    """Fetch real exercise template IDs from the Hevy API."""
    try:
        print("🔍 Fetching real exercise template IDs from Hevy API...")

        # Get API key from environment
        api_key = os.getenv("HEVY_API_KEY")
        if not api_key:
            print("❌ HEVY_API_KEY not found in environment variables!")
            print("💡 Make sure your .env.staging file has HEVY_API_KEY set")
            return {}

        print(f"🔑 Using API key: {api_key[:8]}...")

        # Initialize Hevy API with raw key (not encrypted)
        hevy_api = HevyAPI(api_key, is_encrypted=False)

        # Get all exercises from Hevy API
        print("📡 Calling Hevy API to get exercises...")
        exercise_list = hevy_api.get_all_exercises(include_custom=False)

        if not exercise_list or not exercise_list.exercises:
            print("❌ No exercises found from Hevy API!")
            return {}

        print(f"📊 Found {len(exercise_list.exercises)} exercises from Hevy API")
        print()

        # Group exercises by muscle group and create mapping
        muscle_groups = defaultdict(list)
        exercise_mapping = {}

        for exercise in exercise_list.exercises:
            title = exercise.title
            exercise_id = exercise.id

            if not exercise_id:
                continue

            # Get primary muscle groups
            primary_muscles = []
            for mg in exercise.muscle_groups:
                if mg.is_primary:
                    primary_muscles.append(mg.name.lower())

            # Group by primary muscle
            for muscle in primary_muscles:
                muscle_groups[muscle].append(
                    {
                        "id": exercise_id,
                        "title": title,
                        "equipment": [eq.name for eq in exercise.equipment],
                    }
                )

            # Create mapping for common exercise names
            title_lower = title.lower()
            exercise_mapping[title_lower] = exercise_id

            # Add common variations for seeding script
            if "bench press" in title_lower and "barbell" in title_lower:
                exercise_mapping["bench_press"] = exercise_id
            elif "squat" in title_lower and "barbell" in title_lower:
                exercise_mapping["squat"] = exercise_id
            elif "deadlift" in title_lower and "barbell" in title_lower:
                exercise_mapping["deadlift"] = exercise_id
            elif "pull up" in title_lower or "pullup" in title_lower:
                exercise_mapping["pull_ups"] = exercise_id
            elif "lat pulldown" in title_lower:
                exercise_mapping["lat_pulldown"] = exercise_id
            elif "overhead press" in title_lower or "military press" in title_lower:
                exercise_mapping["overhead_press"] = exercise_id
            elif "bicep curl" in title_lower or "biceps curl" in title_lower:
                exercise_mapping["bicep_curl"] = exercise_id
            elif "leg press" in title_lower:
                exercise_mapping["leg_press"] = exercise_id
            elif "leg curl" in title_lower:
                exercise_mapping["leg_curl"] = exercise_id
            elif "leg extension" in title_lower:
                exercise_mapping["leg_extension"] = exercise_id
            elif (
                "incline" in title_lower
                and "dumbbell" in title_lower
                and "press" in title_lower
            ):
                exercise_mapping["incline_dumbbell_press"] = exercise_id
            elif "push up" in title_lower or "pushup" in title_lower:
                exercise_mapping["push_ups"] = exercise_id
            elif "lateral raise" in title_lower:
                exercise_mapping["lateral_raise"] = exercise_id
            elif "tricep dip" in title_lower:
                exercise_mapping["tricep_dips"] = exercise_id
            elif "plank" in title_lower:
                exercise_mapping["plank"] = exercise_id
            elif "russian twist" in title_lower:
                exercise_mapping["russian_twists"] = exercise_id
            elif "treadmill" in title_lower:
                exercise_mapping["treadmill"] = exercise_id
            elif "stationary bike" in title_lower or "exercise bike" in title_lower:
                exercise_mapping["stationary_bike"] = exercise_id
            elif "barbell row" in title_lower:
                exercise_mapping["barbell_row"] = exercise_id

        # Display results
        print("🏋️ Exercise IDs by Muscle Group:")
        for muscle, exercises in muscle_groups.items():
            print(f"\n{muscle.upper()}:")
            for ex in exercises[:5]:  # Show first 5 exercises per muscle group
                print(f"  {ex['id']} - {ex['title']}")

        print("\n" + "=" * 50)
        print("📋 Exercise ID Mapping for Seeding Script:")
        print("=" * 50)

        # Create a mapping that matches the seeding script format
        seeding_mapping = {}

        # Map common exercises to real IDs
        common_exercises = [
            "bench_press",
            "squat",
            "deadlift",
            "pull_ups",
            "lat_pulldown",
            "overhead_press",
            "bicep_curl",
            "leg_press",
            "leg_curl",
            "leg_extension",
            "incline_dumbbell_press",
            "push_ups",
            "lateral_raise",
            "tricep_dips",
            "plank",
            "russian_twists",
            "treadmill",
            "stationary_bike",
            "barbell_row",
        ]

        for exercise_name in common_exercises:
            if exercise_name in exercise_mapping:
                seeding_mapping[exercise_name] = exercise_mapping[exercise_name]
                print(f"'{exercise_name}': '{exercise_mapping[exercise_name]}'")
            else:
                print(f"❌ '{exercise_name}': NOT FOUND")

        # Save to JSON file for easy reference
        with open("hevy_exercise_ids.json", "w") as f:
            json.dump(
                {
                    "exercise_mapping": exercise_mapping,
                    "muscle_groups": dict(muscle_groups),
                    "seeding_mapping": seeding_mapping,
                    "total_exercises": len(exercise_list.exercises),
                },
                f,
                indent=2,
            )

        print(f"\n💾 Full exercise data saved to 'hevy_exercise_ids.json'")
        print(f"📝 Found {len(seeding_mapping)} common exercises mapped")

        return seeding_mapping

    except Exception as e:
        print(f"❌ Error fetching exercise IDs from Hevy API: {e}")
        import traceback

        traceback.print_exc()
        return {}


def update_seeding_script_with_hevy_ids(seeding_mapping):
    """Update the seeding script with real Hevy exercise IDs."""

    if not seeding_mapping:
        print("❌ No exercise mapping available. Cannot update seeding script.")
        return

    print("\n🔧 Updating seeding script with real Hevy exercise IDs...")

    # Read the current seeding script
    with open("app/scripts/seed_workout_history.py", "r") as f:
        content = f.read()

    # Replace fake IDs with real Hevy IDs
    updated_content = content

    for exercise_name, real_id in seeding_mapping.items():
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

    print("\n🎉 Successfully updated seeding script with real Hevy exercise IDs!")
    print("💡 The seeding script now uses actual exercise IDs from your Hevy account.")


if __name__ == "__main__":
    mapping = fetch_hevy_exercise_ids()
    if mapping:
        print("\n✅ Successfully fetched real exercise IDs from Hevy API!")
        update_seeding_script_with_hevy_ids(mapping)
    else:
        print("\n❌ Failed to fetch exercise IDs from Hevy API.")
        print("💡 Make sure your Hevy API credentials are configured correctly.")
