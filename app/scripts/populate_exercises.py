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
from app.services.hevy_api import HevyAPI
from app.utils.crypto import encrypt_api_key


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

        # Encrypt the API key (this is what the app expects)
        encrypted_key = encrypt_api_key(hevy_api_key)
        hevy_api = HevyAPI(encrypted_key)

        # Fetch exercises from Hevy
        print("📊 Fetching exercises from Hevy API...")
        exercise_list = hevy_api.get_exercises(page_size=1000)  # Get lots of exercises

        if not exercise_list.exercises:
            print("❌ No exercises retrieved from Hevy API!")
            return False

        print(f"✅ Retrieved {len(exercise_list.exercises)} exercises from Hevy")

        # Save exercises to database
        print("💾 Saving exercises to database...")
        db.save_exercises(exercise_list.exercises)

        # Verify exercises were saved
        saved_exercises = db.get_all_exercises()
        print(f"✅ Successfully saved {len(saved_exercises)} exercises to database")

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
        print("💡 You can now run the bootstrap script to populate the vector store:")
        print("   python app/scripts/bootstrap_vectorstore.py")
    else:
        print("\n❌ Failed to populate exercises.")
        print("💡 Check your HEVY_API_KEY environment variable.")
