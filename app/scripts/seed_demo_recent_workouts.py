#!/usr/bin/env python3
"""
Seed recent workout history for demo and test users.
Creates realistic workout history for the past 30 days for:
- demo_user (for production demos)
- test_user_staging (for staging environment testing)
"""

import json
import logging
import os
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Also add the current directory to handle both development and production paths
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from app.config.database import Database
from app.models.user import FitnessGoal, Sex, UnitSystem, UserProfile
from app.services.hevy_api import HevyAPI
from app.utils.crypto import decrypt_api_key

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# User IDs
DEMO_USER_ID = "075ce2423576c5d4a0d8f883aa4ebf7e"  # Demo user (consistent with populate_exercises.py)
TEST_USER_USERNAME = "test_user_staging"  # Test user for staging

# Common exercises with realistic data (using IDs from Hevy API)
EXERCISES = {
    # Chest exercises
    "bench_press": {
        "id": "50DFDFAB-B914-4C89-9EC9-6C3F8B0A5B2C",
        "title": "Bench Press (Barbell)",
        "base_weight": 60,  # kg
        "progression": 2.5,  # kg per week
        "rep_range": (6, 10),
    },
    "incline_dumbbell_press": {
        "id": "A1B2C3D4-E5F6-7890-ABCD-EF1234567890",
        "title": "Incline Dumbbell Press",
        "base_weight": 25,  # kg per dumbbell
        "progression": 1.25,
        "rep_range": (8, 12),
    },
    # Back exercises
    "deadlift": {
        "id": "93472AC1-B5D6-4E7F-8901-234567890ABC",
        "title": "Deadlift (Barbell)",
        "base_weight": 80,
        "progression": 2.5,
        "rep_range": (5, 8),
    },
    "pull_ups": {
        "id": "7C50F118-9A2B-4C5D-6E7F-890123456789",
        "title": "Pull Up",
        "base_weight": 0,
        "progression": 0,
        "rep_range": (6, 12),
    },
    "bent_over_row": {
        "id": "D2387AB1-C4E5-6F78-9012-3456789ABCDE",
        "title": "Bent Over Row (Barbell)",
        "base_weight": 50,
        "progression": 2.5,
        "rep_range": (8, 10),
    },
    # Leg exercises
    "squat": {
        "id": "6622E5A0-1234-5678-90AB-CDEF12345678",
        "title": "Squat (Barbell)",
        "base_weight": 70,
        "progression": 2.5,
        "rep_range": (6, 10),
    },
    "leg_press": {
        "id": "3FD83744-5678-90AB-CDEF-123456789012",
        "title": "Leg Press",
        "base_weight": 120,
        "progression": 5,
        "rep_range": (10, 15),
    },
    # Shoulder exercises
    "overhead_press": {
        "id": "073032BB-4567-890A-BCDE-F123456789AB",
        "title": "Overhead Press (Barbell)",
        "base_weight": 40,
        "progression": 1.25,
        "rep_range": (6, 10),
    },
    "lateral_raise": {
        "id": "DE68C825-6789-0ABC-DEF1-23456789ABCD",
        "title": "Lateral Raise (Dumbbell)",
        "base_weight": 8,
        "progression": 1.25,
        "rep_range": (12, 15),
    },
    # Arm exercises
    "bicep_curl": {
        "id": "01A35BF9-7890-ABCD-EF12-3456789ABCDE",
        "title": "Bicep Curl (Dumbbell)",
        "base_weight": 12,
        "progression": 1.25,
        "rep_range": (10, 15),
    },
}

# Workout splits and patterns
WORKOUT_SPLITS = {
    "upper_lower": {
        "days": ["upper", "lower", "upper", "lower"],
        "exercises": {
            "upper": [
                "bench_press",
                "bent_over_row",
                "overhead_press",
                "bicep_curl",
            ],
            "lower": [
                "squat",
                "deadlift",
                "leg_press",
            ],
        },
    },
}


class RecentWorkoutSeeder:
    """Generate realistic recent workout history for demo and test users."""

    def __init__(self, db: Database, hevy_api: Optional[HevyAPI] = None):
        self.db = db
        self.hevy_api = hevy_api

    def create_or_find_test_user(self) -> Optional[str]:
        """Create or find the test user for staging."""
        logger.info(f"Creating or finding test user: {TEST_USER_USERNAME}")

        # Check if user already exists by username
        existing_user = self.db.get_user_by_username(TEST_USER_USERNAME)
        if existing_user:
            logger.info(f"✅ Test user already exists with ID: {existing_user['_id']}")
            return existing_user["_id"]

        # Create new test user
        try:
            user = UserProfile.create_user(
                username=TEST_USER_USERNAME,
                email="test@staging.formava.com",
                password="test_password_123",
                height_cm=180,
                weight_kg=80,
                sex=Sex.MALE,
                age=25,
                fitness_goals=[FitnessGoal.STRENGTH, FitnessGoal.MUSCLE_GAIN],
                experience_level="intermediate",
                preferred_workout_days=4,
                preferred_workout_duration=75,
                preferred_units=UnitSystem.METRIC,
            )

            user_dict = user.to_dict()
            user_id, _ = self.db.save_document(user_dict)
            logger.info(f"✅ Created test user {TEST_USER_USERNAME} with ID: {user_id}")
            return user_id
        except Exception as e:
            logger.error(f"❌ Failed to create test user: {e}")
            return None

    def calculate_exercise_weight(self, exercise_name: str, week_number: int) -> float:
        """Calculate weight for an exercise based on progression."""
        exercise = EXERCISES[exercise_name]
        base_weight = exercise["base_weight"]
        progression = exercise["progression"]

        # Add some randomness to progression
        progression_factor = week_number + random.uniform(-0.5, 0.5)
        weight = base_weight + (progression * progression_factor)

        # Round to nearest practical weight
        if weight > 0:
            weight = round(weight / 2.5) * 2.5  # Round to nearest 2.5kg

        return max(0, weight)

    def generate_sets(self, exercise_name: str, week_number: int) -> List[Dict]:
        """Generate realistic sets for an exercise."""
        exercise = EXERCISES[exercise_name]
        rep_range = exercise["rep_range"]

        # Number of sets (3-4 for most exercises)
        num_sets = random.choice([3, 3, 4])  # Bias toward 3 sets

        sets = []
        weight = self.calculate_exercise_weight(exercise_name, week_number)

        for i in range(num_sets):
            reps = random.randint(rep_range[0], rep_range[1])

            # Add some fatigue effect - later sets might have fewer reps
            if i > 0 and random.random() < 0.3:
                reps = max(rep_range[0], reps - random.randint(1, 2))

            sets.append(
                {
                    "type": "normal",
                    "weight_kg": weight if weight > 0 else None,
                    "reps": reps,
                    "duration_seconds": None,
                    "distance_meters": None,
                    "rpe": random.choice([6, 7, 7, 8, 8, 9]),  # RPE 6-9
                }
            )

        return sets

    def generate_workout(
        self, user_id: str, date: datetime, workout_type: str, week_number: int
    ) -> Dict:
        """Generate a complete workout for a given date and type."""
        split = WORKOUT_SPLITS["upper_lower"]
        exercises_for_type = split["exercises"][workout_type]

        # Select all exercises for the workout type
        selected_exercises = exercises_for_type.copy()

        workout_exercises = []
        for exercise_name in selected_exercises:
            exercise_data = EXERCISES[exercise_name]
            sets = self.generate_sets(exercise_name, week_number)

            # Generate occasional notes
            notes = None
            if random.random() < 0.3:  # 30% chance of notes
                notes_options = [
                    "Felt strong today",
                    "Form was on point",
                    "Challenging but good",
                    "Increased weight from last time",
                    "Good pump",
                    "Focus on form and depth",
                    "Control the descent",
                    "Keep back straight",
                    "Full range of motion",
                    "Maintain proper form",
                ]
                notes = random.choice(notes_options)

            workout_exercises.append(
                {
                    "exercise_template_id": exercise_data["id"],
                    "superset_id": None,
                    "notes": notes,
                    "sets": sets,
                }
            )

        # Calculate workout duration (45-75 minutes)
        duration_minutes = random.randint(45, 75)

        # Generate realistic workout times (morning or evening)
        if random.random() < 0.6:  # 60% morning workouts
            hour = random.randint(6, 9)  # 6-9 AM
        else:  # 40% evening workouts
            hour = random.randint(17, 20)  # 5-8 PM

        start_time = date.replace(
            hour=hour,
            minute=random.choice([0, 15, 30, 45]),
            second=0,
            microsecond=0,
        )
        end_time = start_time + timedelta(minutes=duration_minutes)

        # Generate workout titles
        title_templates = [
            f"{workout_type.title()} Body Workout",
            f"Strong {workout_type.title()} Day",
            f"{workout_type.title()} Training Session",
            f"{workout_type.title()} Body Focus",
        ]
        workout_title = random.choice(title_templates)

        return {
            "id": str(uuid.uuid4()),
            "title": workout_title,
            "description": f"Focused {workout_type} body training session",
            "start_time": start_time.isoformat().replace("+00:00", "Z"),
            "end_time": end_time.isoformat().replace("+00:00", "Z"),
            "user_id": user_id,
            "type": "workout",
            "exercises": workout_exercises,
        }

    def seed_recent_workouts_for_user(
        self, user_id: str, username: str, days: int = 30
    ) -> List[str]:
        """Generate recent workout history for a specific user."""
        logger.info(f"Seeding {days} days of recent workout history for {username}")

        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        # Generate workout schedule (3-4 days per week)
        workout_days = []
        current_date = start_date
        workout_pattern = ["upper", "lower", "upper", "lower"]
        pattern_index = 0

        while current_date <= end_date:
            # Skip some days to simulate rest days (aim for ~4 workouts per week)
            if current_date.weekday() not in [6]:  # Skip most Sundays
                if random.random() < 0.55:  # 55% chance of working out
                    workout_type = workout_pattern[pattern_index % len(workout_pattern)]
                    week_number = (current_date - start_date).days // 7

                    workout_days.append(
                        {
                            "date": current_date,
                            "type": workout_type,
                            "week": week_number,
                        }
                    )
                    pattern_index += 1

            current_date += timedelta(days=1)

        # Generate workouts
        workout_ids = []
        for workout_day in workout_days:
            workout = self.generate_workout(
                user_id=user_id,
                date=workout_day["date"],
                workout_type=workout_day["type"],
                week_number=workout_day["week"],
            )

            try:
                # Create workout in Hevy platform if API is available
                if self.hevy_api:
                    logger.info(
                        f"Creating workout in Hevy platform: {workout['title']}"
                    )
                    hevy_workout_id = self.hevy_api.create_workout(workout)
                    if hevy_workout_id:
                        # Update workout with Hevy ID before saving to database
                        workout["hevy_id"] = hevy_workout_id
                        logger.info(
                            f"✅ Created workout in Hevy with ID: {hevy_workout_id}"
                        )
                    else:
                        logger.warning(
                            f"⚠️ Failed to create workout in Hevy, saving to database only"
                        )

                # Save to local database
                workout_id = self.db.save_workout(workout, user_id=user_id)
                workout_ids.append(workout_id)
                logger.info(
                    f"Created workout: {workout['title']} on {workout_day['date'].strftime('%Y-%m-%d')} for {username}"
                )
            except Exception as e:
                logger.error(f"Error saving workout for {username}: {e}")

        logger.info(
            f"Successfully created {len(workout_ids)} recent workouts for {username}"
        )
        return workout_ids

    def seed_demo_user_workouts(self, days: int = 30) -> List[str]:
        """Generate recent workout history for the demo user."""
        # First try to find by hardcoded ID
        demo_user = self.db.get_document(DEMO_USER_ID)

        if not demo_user:
            # If not found by ID, try to find by username
            logger.info(
                f"Demo user not found by ID {DEMO_USER_ID}, searching by username..."
            )
            demo_user = self.db.get_user_by_username("demo_user")

        if not demo_user:
            logger.error("❌ Demo user not found by ID or username!")
            logger.error(
                "Please run populate_exercises.py first to create the demo user."
            )
            return []

        # Use the actual user ID from the database
        actual_user_id = demo_user.get("_id") or demo_user.get("id")
        username = demo_user.get("username", "demo_user")
        logger.info(f"✅ Found demo user: {username} (ID: {actual_user_id})")

        return self.seed_recent_workouts_for_user(actual_user_id, username, days)

    def seed_test_user_workouts(self, days: int = 30) -> List[str]:
        """Generate recent workout history for the test user."""
        # Create or find test user
        test_user_id = self.create_or_find_test_user()
        if not test_user_id:
            logger.error("❌ Failed to create or find test user")
            return []

        return self.seed_recent_workouts_for_user(
            test_user_id, TEST_USER_USERNAME, days
        )


def main():
    """Main function to run the seeding script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Seed recent workout history for users"
    )
    parser.add_argument(
        "--user",
        choices=["demo", "test", "both"],
        default="both",
        help="Which user to seed workouts for (default: both)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days of workout history to generate (default: 30)",
    )

    args = parser.parse_args()

    logger.info("Starting recent workout seeding script")
    logger.info(f"Target user(s): {args.user}")
    logger.info(f"Days of history: {args.days}")

    # Initialize database connection
    try:
        db = Database()
        logger.info("✅ Successfully connected to database")
    except Exception as e:
        logger.error(f"❌ Failed to connect to database: {e}")
        sys.exit(1)

    # Initialize Hevy API with demo API key from environment
    hevy_api = None
    demo_api_key = os.getenv("HEVY_API_KEY")
    if demo_api_key:
        try:
            hevy_api = HevyAPI(demo_api_key, is_encrypted=False)
            logger.info("✅ Successfully initialized Hevy API")
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize Hevy API: {e}")
            logger.warning("Will create workouts in database only")
    else:
        logger.warning("⚠️ No HEVY_API_KEY environment variable found")
        logger.warning("Will create workouts in database only")

    # Initialize seeder
    seeder = RecentWorkoutSeeder(db, hevy_api)

    total_workouts = 0
    success = True

    # Seed demo user workouts
    if args.user in ["demo", "both"]:
        logger.info("\n" + "=" * 50)
        logger.info("🎯 SEEDING DEMO USER WORKOUTS")
        logger.info("=" * 50)

        demo_workout_ids = seeder.seed_demo_user_workouts(days=args.days)
        if demo_workout_ids:
            total_workouts += len(demo_workout_ids)
            logger.info(f"✅ Demo user: Created {len(demo_workout_ids)} workouts")
        else:
            logger.error("❌ Demo user: Failed to create workouts")
            success = False

    # Seed test user workouts
    if args.user in ["test", "both"]:
        logger.info("\n" + "=" * 50)
        logger.info("🧪 SEEDING TEST USER WORKOUTS")
        logger.info("=" * 50)

        test_workout_ids = seeder.seed_test_user_workouts(days=args.days)
        if test_workout_ids:
            total_workouts += len(test_workout_ids)
            logger.info(f"✅ Test user: Created {len(test_workout_ids)} workouts")
        else:
            logger.error("❌ Test user: Failed to create workouts")
            success = False

    # Final summary
    logger.info("\n" + "=" * 50)
    logger.info("📊 SEEDING SUMMARY")
    logger.info("=" * 50)

    if success and total_workouts > 0:
        logger.info(f"🎉 SUCCESS! Created {total_workouts} total recent workouts")
        logger.info(
            "💪 Users now have recent workout history for compelling AI recommendations!"
        )

        if args.user in ["demo", "both"]:
            logger.info("🎯 Demo user ready for production demos")
        if args.user in ["test", "both"]:
            logger.info("🧪 Test user ready for staging testing")
            logger.info("   Login: test_user_staging / test_password_123")
    else:
        logger.error(f"❌ FAILED! Only created {total_workouts} workouts")
        sys.exit(1)


if __name__ == "__main__":
    main()
