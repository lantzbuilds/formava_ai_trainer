#!/usr/bin/env python3
"""
Script to create or update the demo user account.
This ensures the demo user exists for staging and production environments.
"""

import os
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.database import Database
from app.models.user import FitnessGoal, Sex, UnitSystem, UserProfile
from app.utils.crypto import encrypt_api_key


def create_demo_user():
    """Create or update the demo user account."""
    print("🔄 Creating/updating demo user account...")

    try:
        # Initialize services
        db = Database()

        # Demo user details
        demo_user_id = "075ce2423576c5d4a0d8f883aa4ebf7e"
        demo_username = "demo_user"
        demo_email = "demo_user@formava.ai"
        demo_password = "demo_password_123"

        # Check if demo user already exists by ID
        existing_user = db.get_document(demo_user_id)
        if existing_user and existing_user.get("type") == "user_profile":
            print(f"✅ Demo user already exists with ID: {demo_user_id}")
            print(f"   Username: {existing_user.get('username', 'Unknown')}")
            print(f"   Email: {existing_user.get('email', 'Unknown')}")
            return True

        # Check if demo user exists by username
        existing_user = db.get_user_by_username(demo_username)
        if existing_user:
            print(f"⚠️  Demo user exists with different ID: {existing_user['_id']}")
            print(f"   Expected ID: {demo_user_id}")
            print(f"   Using existing user...")
            return True

        # Get Hevy API key from environment for demo user
        hevy_api_key = os.getenv("HEVY_API_KEY")
        if hevy_api_key:
            encrypted_key = encrypt_api_key(hevy_api_key)
            print("✅ Demo user will be configured with Hevy API access")
        else:
            encrypted_key = None
            print("⚠️  No HEVY_API_KEY found - demo user will not have Hevy access")

        # Create demo user with realistic profile
        demo_user = UserProfile.create_user(
            username=demo_username,
            email=demo_email,
            password=demo_password,
            height_cm=175,  # 5'9"
            weight_kg=75,  # 165 lbs
            sex=Sex.MALE,
            age=30,
            fitness_goals=[FitnessGoal.STRENGTH, FitnessGoal.MUSCLE_GAIN],
            experience_level="intermediate",
            preferred_workout_days=4,
            preferred_workout_duration=75,
            preferred_units=UnitSystem.IMPERIAL,
            hevy_api_key=encrypted_key,
        )

        # Convert to dict and set the specific ID
        user_dict = demo_user.to_dict()
        user_dict["_id"] = demo_user_id

        # Save to database
        saved_id, saved_rev = db.save_document(user_dict)
        print(f"✅ Created demo user with ID: {saved_id}")
        print(f"   Username: {demo_username}")
        print(f"   Email: {demo_email}")
        print(f"   Password: {demo_password}")

        return True

    except Exception as e:
        print(f"❌ Error creating demo user: {e}")
        return False


if __name__ == "__main__":
    success = create_demo_user()
    if success:
        print("\n🎉 Demo user is ready!")
        print("💡 Users can now click 'Use Demo Account' on the landing page.")
    else:
        print("\n❌ Failed to create demo user.")
        print("💡 Check the error messages above.")
