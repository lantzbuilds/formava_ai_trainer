#!/usr/bin/env python3
"""
Script to fetch real exercise template IDs from the database.
This will help update the seeding script to use actual exercise IDs.
"""
import json
import os
import sys
from collections import defaultdict

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config.database import Database


def get_real_exercise_ids():
    """Fetch real exercise template IDs from the database."""
    try:
        # Initialize database connection
        db = Database()

        print("🔍 Fetching real exercise template IDs from database...")
        print(f"Connected to database: {db.couchdb_db}")
        print()

        # Get all exercises from the database
        all_exercises = db.get_all_exercises()

        if not all_exercises:
            print("❌ No exercises found in database!")
            print("💡 You may need to sync exercises from Hevy first.")
            return {}

        print(f"📊 Found {len(all_exercises)} exercises in database")
        print()

        # Group exercises by muscle group for easier mapping
        muscle_groups = defaultdict(list)
        exercise_mapping = {}

        for exercise in all_exercises:
            title = exercise.get("title", "Unknown")
            exercise_id = exercise.get("id") or exercise.get("exercise_template_id")

            if not exercise_id:
                continue

            # Get primary muscle groups
            primary_muscles = []
            for mg in exercise.get("muscle_groups", []):
                if mg.get("is_primary", False):
                    primary_muscles.append(mg.get("name", "").lower())

            # Group by primary muscle
            for muscle in primary_muscles:
                muscle_groups[muscle].append(
                    {
                        "id": exercise_id,
                        "title": title,
                        "equipment": [
                            eq.get("name", "") for eq in exercise.get("equipment", [])
                        ],
                    }
                )

            # Create mapping for common exercise names
            title_lower = title.lower()
            exercise_mapping[title_lower] = exercise_id

            # Add some common variations
            if "bench press" in title_lower:
                exercise_mapping["bench_press"] = exercise_id
            elif "squat" in title_lower and "barbell" in title_lower:
                exercise_mapping["squat"] = exercise_id
            elif "deadlift" in title_lower:
                exercise_mapping["deadlift"] = exercise_id
            elif "pull up" in title_lower or "pullup" in title_lower:
                exercise_mapping["pull_ups"] = exercise_id
            elif "lat pulldown" in title_lower:
                exercise_mapping["lat_pulldown"] = exercise_id
            elif "overhead press" in title_lower:
                exercise_mapping["overhead_press"] = exercise_id
            elif "bicep curl" in title_lower or "biceps curl" in title_lower:
                exercise_mapping["bicep_curl"] = exercise_id
            elif "leg press" in title_lower:
                exercise_mapping["leg_press"] = exercise_id

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
        ]

        for exercise_name in common_exercises:
            if exercise_name in exercise_mapping:
                seeding_mapping[exercise_name] = exercise_mapping[exercise_name]
                print(f"'{exercise_name}': '{exercise_mapping[exercise_name]}'")

        # Save to JSON file for easy reference
        with open("real_exercise_ids.json", "w") as f:
            json.dump(
                {
                    "exercise_mapping": exercise_mapping,
                    "muscle_groups": dict(muscle_groups),
                    "seeding_mapping": seeding_mapping,
                },
                f,
                indent=2,
            )

        print(f"\n💾 Full exercise data saved to 'real_exercise_ids.json'")
        print(f"📝 Found {len(seeding_mapping)} common exercises mapped")

        return seeding_mapping

    except Exception as e:
        print(f"❌ Error fetching exercise IDs: {e}")
        return {}


if __name__ == "__main__":
    mapping = get_real_exercise_ids()
    if mapping:
        print("\n✅ Successfully fetched real exercise IDs!")
        print("💡 Now you can update the seeding script to use these real IDs.")
    else:
        print("\n❌ Failed to fetch exercise IDs.")
        print("💡 Make sure you have synced exercises from Hevy first.")
