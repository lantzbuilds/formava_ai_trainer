#!/usr/bin/env python3
"""
Test script to verify routine generation works correctly with different measurement units.
Tests both metric and imperial unit preferences.
"""
import json
import os
import sys
from datetime import datetime, timezone

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config.database import Database
from app.services.openai_service import OpenAIService


def test_routine_generation_units():
    """Test routine generation with different measurement units."""
    try:
        print("🧪 Testing routine generation with different measurement units...")
        print()

        # Initialize services
        db = Database()
        openai_service = OpenAIService()

        # Get test user
        test_user = db.get_user_by_username("test_user_staging")
        if not test_user:
            print("❌ Test user 'test_user_staging' not found!")
            print("💡 Run the seeding script first to create test data")
            return False

        print(f"✅ Found test user: {test_user['username']}")
        print(f"   User ID: {test_user['_id']}")
        print()

        # Test configurations for different units
        test_configs = [
            {
                "name": "Imperial Units Test",
                "preferred_units": "imperial",
                "expected_weight_format": "lbs equivalent (in kg)",
            },
            {
                "name": "Metric Units Test",
                "preferred_units": "metric",
                "expected_weight_format": "kg",
            },
        ]

        for config in test_configs:
            print(f"🔬 {config['name']}")
            print(f"   Units: {config['preferred_units']}")
            print(f"   Expected weights: {config['expected_weight_format']}")

            # Create user context with specific unit preference
            user_context = {
                "user_id": test_user["_id"],
                "user_profile": {
                    "experience_level": "intermediate",
                    "fitness_goals": ["Muscle Building", "Strength"],
                    "injuries": [],
                    "preferred_workout_duration": 60,
                    "preferred_units": config["preferred_units"],
                    "workout_schedule": {"days_per_week": 4},
                },
                "generation_preferences": {
                    "split_type": "upper_lower",
                    "include_cardio": False,
                },
            }

            # Generate a routine
            print("   📝 Generating upper body routine...")
            routine = openai_service.generate_routine(
                day="Monday",
                focus="upper body",
                context=user_context,
                include_cardio=False,
            )

            if not routine:
                print("   ❌ Failed to generate routine")
                continue

            print("   ✅ Routine generated successfully!")

            # Analyze the generated routine
            if "hevy_api" in routine and "routine" in routine["hevy_api"]:
                exercises = routine["hevy_api"]["routine"]["exercises"]
                print(f"   📊 Generated {len(exercises)} exercises")

                # Check weight assignments
                weight_exercises = []
                bodyweight_exercises = []

                for exercise in exercises:
                    exercise_name = exercise.get("name", "Unknown")
                    sets = exercise.get("sets", [])

                    has_weight = any(s.get("weight_kg", 0) > 0 for s in sets)

                    if has_weight:
                        weights = [
                            s.get("weight_kg", 0)
                            for s in sets
                            if s.get("weight_kg", 0) > 0
                        ]
                        weight_exercises.append(
                            {
                                "name": exercise_name,
                                "weights": weights,
                                "sets_count": len(sets),
                            }
                        )
                    else:
                        bodyweight_exercises.append(exercise_name)

                print(f"   🏋️ Weight exercises: {len(weight_exercises)}")
                print(f"   🤸 Bodyweight exercises: {len(bodyweight_exercises)}")

                # Show sample weights for imperial vs metric
                if weight_exercises:
                    sample_exercise = weight_exercises[0]
                    sample_weights = sample_exercise["weights"]

                    print(f"   📏 Sample weights from '{sample_exercise['name']}':")

                    if config["preferred_units"] == "imperial":
                        # Check if weights are using imperial-friendly values
                        imperial_weights = [
                            2.3,
                            4.5,
                            6.8,
                            9.1,
                            11.3,
                            13.6,
                            15.9,
                            18.1,
                            20.4,
                            22.7,
                            25.0,
                            27.2,
                            29.5,
                            31.8,
                            34.0,
                            36.3,
                            38.6,
                            40.8,
                            43.1,
                            45.4,
                            47.6,
                            49.9,
                            52.2,
                            54.4,
                            56.7,
                            59.0,
                            61.2,
                            63.5,
                            65.8,
                            68.0,
                            70.3,
                            72.6,
                            74.8,
                            77.1,
                            79.4,
                            81.6,
                            83.9,
                            86.2,
                            88.5,
                            90.7,
                        ]

                        for weight in sample_weights[:3]:  # Show first 3 weights
                            # Convert to lbs for display
                            lbs = weight * 2.20462
                            is_imperial_friendly = any(
                                abs(weight - iw) < 0.1 for iw in imperial_weights
                            )
                            status = "✅" if is_imperial_friendly else "⚠️"
                            print(f"      {status} {weight}kg ({lbs:.1f}lbs)")
                    else:
                        # For metric, just show the weights
                        for weight in sample_weights[:3]:
                            print(f"      ✅ {weight}kg")

                # Validate exercise template IDs
                valid_ids = 0
                invalid_ids = 0

                for exercise in exercises:
                    exercise_id = exercise.get("exercise_template_id")
                    if (
                        exercise_id and len(exercise_id) > 5
                    ):  # Real IDs should be longer than fake ones
                        valid_ids += 1
                    else:
                        invalid_ids += 1
                        print(f"   ⚠️ Potentially invalid exercise ID: {exercise_id}")

                print(f"   🆔 Exercise IDs: {valid_ids} valid, {invalid_ids} invalid")

                # Save sample routine for inspection
                filename = f"sample_routine_{config['preferred_units']}.json"
                with open(filename, "w") as f:
                    json.dump(routine, f, indent=2)
                print(f"   💾 Sample routine saved to {filename}")

            print()

        print("🎉 Unit testing completed!")
        return True

    except Exception as e:
        print(f"❌ Error during unit testing: {e}")
        import traceback

        traceback.print_exc()
        return False


def analyze_weight_patterns():
    """Analyze weight patterns in generated routines."""
    print("📊 Analyzing weight patterns...")

    # Load saved routines
    routines = {}
    for unit_type in ["imperial", "metric"]:
        filename = f"sample_routine_{unit_type}.json"
        try:
            with open(filename, "r") as f:
                routines[unit_type] = json.load(f)
        except FileNotFoundError:
            print(f"⚠️ {filename} not found - run unit test first")
            return

    print("\n🔍 Weight Analysis:")
    for unit_type, routine in routines.items():
        print(f"\n{unit_type.upper()} Routine:")

        if "hevy_api" in routine and "routine" in routine["hevy_api"]:
            exercises = routine["hevy_api"]["routine"]["exercises"]

            all_weights = []
            for exercise in exercises:
                for set_data in exercise.get("sets", []):
                    weight = set_data.get("weight_kg", 0)
                    if weight > 0:
                        all_weights.append(weight)

            if all_weights:
                print(f"  Total weight values: {len(all_weights)}")
                print(
                    f"  Weight range: {min(all_weights):.1f}kg - {max(all_weights):.1f}kg"
                )
                print(f"  Average weight: {sum(all_weights)/len(all_weights):.1f}kg")

                # Show unique weights
                unique_weights = sorted(set(all_weights))
                print(
                    f"  Unique weights: {unique_weights[:10]}..."
                    if len(unique_weights) > 10
                    else f"  Unique weights: {unique_weights}"
                )

                # For imperial, check compliance with standard values
                if unit_type == "imperial":
                    imperial_standard = [
                        2.3,
                        4.5,
                        6.8,
                        9.1,
                        11.3,
                        13.6,
                        15.9,
                        18.1,
                        20.4,
                        22.7,
                        25.0,
                        27.2,
                        29.5,
                        31.8,
                        34.0,
                        36.3,
                        38.6,
                        40.8,
                        43.1,
                        45.4,
                        47.6,
                        49.9,
                        52.2,
                        54.4,
                        56.7,
                        59.0,
                        61.2,
                        63.5,
                        65.8,
                        68.0,
                        70.3,
                        72.6,
                        74.8,
                        77.1,
                        79.4,
                        81.6,
                        83.9,
                        86.2,
                        88.5,
                        90.7,
                    ]

                    compliant_weights = 0
                    for weight in all_weights:
                        if any(abs(weight - std) < 0.1 for std in imperial_standard):
                            compliant_weights += 1

                    compliance_rate = (compliant_weights / len(all_weights)) * 100
                    print(
                        f"  Imperial compliance: {compliant_weights}/{len(all_weights)} ({compliance_rate:.1f}%)"
                    )


if __name__ == "__main__":
    success = test_routine_generation_units()
    if success:
        analyze_weight_patterns()
    else:
        print("❌ Unit testing failed")
