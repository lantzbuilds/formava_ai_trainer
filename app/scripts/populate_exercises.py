#!/usr/bin/env python3
"""
Script to populate production database with exercises from Hevy API.
Run this once to seed the database with exercises.
"""

import os
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.database import Database
from app.models.user import FitnessGoal, Sex, UnitSystem, UserProfile
from app.services.hevy_api import HevyAPI
from app.utils.crypto import encrypt_api_key


def create_demo_user(db, hevy_api_key=None):
    """Create the demo user account if it doesn't exist."""
    print("🔄 Ensuring demo user exists...")

    demo_user_id = "075ce2423576c5d4a0d8f883aa4ebf7e"
    demo_username = "demo_user"

    # Check if demo user already exists by ID
    existing_user = db.get_document(demo_user_id)
    if existing_user and existing_user.get("type") == "user_profile":
        print(
            f"✅ Demo user already exists: {existing_user.get('username', 'Unknown')}"
        )
        return True

    # Check by username as fallback
    existing_user = db.get_user_by_username(demo_username)
    if existing_user:
        print(f"✅ Demo user exists with different ID: {existing_user['_id']}")
        return True

    try:
        # Encrypt API key if provided
        encrypted_key = None
        if hevy_api_key:
            encrypted_key = encrypt_api_key(hevy_api_key)

        # Create demo user
        demo_user = UserProfile.create_user(
            username=demo_username,
            email="demo_user@formava.ai",
            password="demo_password_123",
            height_cm=175,
            weight_kg=75,
            sex=Sex.MALE,
            age=30,
            fitness_goals=[FitnessGoal.STRENGTH, FitnessGoal.MUSCLE_GAIN],
            experience_level="intermediate",
            preferred_workout_days=4,
            preferred_workout_duration=75,
            preferred_units=UnitSystem.IMPERIAL,
            hevy_api_key=encrypted_key,
        )

        # Set specific ID and save
        user_dict = demo_user.to_dict()
        user_dict["_id"] = demo_user_id
        db.save_document(user_dict)
        print(f"✅ Created demo user: {demo_username}")
        return True

    except Exception as e:
        print(f"⚠️  Failed to create demo user: {e}")
        return False


def populate_exercises():
    """Populate the database with exercises from Hevy API."""
    print("🔄 Populating production database with exercises...")

    # Get Hevy API key from environment
    hevy_api_key = os.getenv("HEVY_API_KEY")
    if not hevy_api_key:
        print("❌ HEVY_API_KEY environment variable not set!")
        print("💡 You need a demo Hevy account API key to populate exercises.")
        return False

    try:
        # Initialize services
        db = Database()

        # Create demo user first
        create_demo_user(db, hevy_api_key)

        # Encrypt the API key (this is what the app expects)
        encrypted_key = encrypt_api_key(hevy_api_key)
        hevy_api = HevyAPI(encrypted_key)

        # Fetch base exercises from Hevy
        print("📊 Fetching all base exercises from Hevy API (paginated)...")
        base_exercise_list = hevy_api.get_all_exercises(
            max_pages=50, include_custom=False
        )  # Get all base exercises

        if not base_exercise_list.exercises:
            print("❌ No base exercises retrieved from Hevy API!")
            return False

        print(
            f"✅ Retrieved {len(base_exercise_list.exercises)} base exercises from Hevy"
        )

        # Save base exercises to database
        print("💾 Saving base exercises to database...")
        base_exercises_data = [
            exercise.model_dump() for exercise in base_exercise_list.exercises
        ]
        db.save_exercises(base_exercises_data)

        # Fetch custom exercises from the demo account
        print("📊 Fetching custom exercises from demo account...")
        custom_exercise_list = hevy_api.get_all_exercises(
            max_pages=10, include_custom=True
        )

        custom_exercises_count = 0
        if custom_exercise_list.exercises:
            # Filter to only include custom exercises
            custom_exercises = [
                exercise
                for exercise in custom_exercise_list.exercises
                if exercise.is_custom
            ]

            if custom_exercises:
                print(
                    f"✅ Retrieved {len(custom_exercises)} custom exercises from demo account"
                )
                # Save custom exercises with demo user ID
                custom_exercises_data = [
                    exercise.model_dump() for exercise in custom_exercises
                ]
                demo_user_id = "075ce2423576c5d4a0d8f883aa4ebf7e"
                db.save_exercises(
                    custom_exercises_data, is_custom=True, user_id=demo_user_id
                )
                custom_exercises_count = len(custom_exercises)
            else:
                print("ℹ️  No custom exercises found in demo account")
        else:
            print("ℹ️  No custom exercises found in demo account")

        total_exercises = len(base_exercise_list.exercises) + custom_exercises_count

        # Verify exercises were saved
        saved_exercises = db.get_all_exercises()
        print(
            f"✅ Successfully saved {total_exercises} exercises to database ({len(base_exercise_list.exercises)} base + {custom_exercises_count} custom)"
        )

        # Sample some exercises
        if saved_exercises:
            print(f"📝 Sample exercises:")
            for i, exercise in enumerate(saved_exercises[:3]):
                print(
                    f"   {i+1}. {exercise.get('title', 'Unknown')} (ID: {exercise.get('id', 'Unknown')})"
                )

        return True

    except Exception as e:
        print(f"❌ Error populating exercises: {e}")
        return False


if __name__ == "__main__":
    success = populate_exercises()
    if success:
        print("\n🎉 Production database is now ready!")
        print("💡 Now bootstrapping vector store...")

        # Automatically bootstrap the vector store
        try:
            from app.scripts.bootstrap_vectorstore import bootstrap_vectorstore

            bootstrap_success = bootstrap_vectorstore()
            if bootstrap_success:
                print("✅ Vector store bootstrapped successfully!")
                print("\n🚀 Deployment is complete and ready!")
            else:
                print("⚠️  Vector store bootstrap failed, but exercises are populated.")
                print("💡 You may need to run bootstrap_vectorstore.py manually.")
        except Exception as e:
            print(f"⚠️  Vector store bootstrap failed: {e}")
            print("💡 You may need to run bootstrap_vectorstore.py manually.")
    else:
        print("\n❌ Failed to populate exercises.")
        print("💡 Check your HEVY_API_KEY environment variable.")
