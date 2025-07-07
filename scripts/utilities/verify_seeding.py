#!/usr/bin/env python3
"""
Verification script to check if workout seeding was successful.
"""
import os
import sys
from datetime import datetime, timezone

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config.database import Database


def verify_seeding():
    """Verify that the seeding script created workout data."""
    try:
        # Initialize database connection
        db = Database()

        print("🔍 Verifying seeding results...")
        print(f"Connected to database: {db.couchdb_db}")
        print(f"Database URL: {db.couchdb_url}")
        print()

        # Check if test user exists
        test_user = db.get_user_by_username("test_user_staging")
        if test_user:
            print("✅ Test user found!")
            print(f"   Username: {test_user['username']}")
            print(f"   User ID: {test_user['_id']}")
            print()

            # Get workout count for test user
            all_workouts = db.get_all_workouts()
            user_workouts = [
                w for w in all_workouts if w.get("user_id") == test_user["_id"]
            ]

            print(f"📊 Workout Statistics:")
            print(f"   Total workouts in database: {len(all_workouts)}")
            print(f"   Workouts for test user: {len(user_workouts)}")
            print()

            if user_workouts:
                print("🏋️ Sample workout data:")
                latest_workout = max(
                    user_workouts, key=lambda w: w.get("start_time", "")
                )
                print(
                    f"   Latest workout date: {latest_workout.get('start_time', 'N/A')}"
                )
                print(
                    f"   Exercise count: {latest_workout.get('exercise_count', 'N/A')}"
                )
                print(
                    f"   Duration: {latest_workout.get('duration_minutes', 'N/A')} minutes"
                )

                if "exercises" in latest_workout and latest_workout["exercises"]:
                    print(
                        f"   First exercise: {latest_workout['exercises'][0].get('title', 'N/A')}"
                    )
                print()

                # Date range analysis
                dates = [
                    w.get("start_time", "")
                    for w in user_workouts
                    if w.get("start_time")
                ]
                if dates:
                    print(f"📅 Date range:")
                    print(f"   Earliest: {min(dates)}")
                    print(f"   Latest: {max(dates)}")
                    print()

                print("✅ Seeding appears successful!")
                return True
            else:
                print("❌ No workouts found for test user")
                return False

        else:
            print("❌ Test user 'test_user_staging' not found")
            return False

    except Exception as e:
        print(f"❌ Error during verification: {e}")
        return False


if __name__ == "__main__":
    success = verify_seeding()
    sys.exit(0 if success else 1)
