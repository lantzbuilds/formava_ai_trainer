#!/usr/bin/env python3
"""
Script to seed recent workout history for the test user.
"""

import logging
import random
from datetime import datetime, timedelta, timezone

from config.database import Database
from models.user import UserProfile
from services.hevy_api import HevyAPI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_test_user() -> UserProfile:
    """Get the existing test user with username 'test1'."""
    db = Database()

    # Get user by username
    user_doc = db.get_user_by_username("test1")

    if not user_doc:
        logger.error("Test user with username 'test1' not found")
        return None

    test_user = UserProfile(**user_doc)

    if not test_user.hevy_api_key:
        logger.error("Hevy API key not configured for test user 'test1'")
        return None

    logger.info(f"Found test user: {test_user.username}")
    return test_user


def create_workout(hevy_api: HevyAPI, workout_date: datetime) -> bool:
    """Create a workout in Hevy.

    Args:
        hevy_api: HevyAPI instance
        workout_date: Date for the workout

    Returns:
        True if successful, False otherwise
    """
    try:
        # Calculate workout duration (30-60 minutes)
        duration_minutes = random.randint(30, 60)
        start_time = workout_date
        end_time = start_time + timedelta(minutes=duration_minutes)

        # Sample exercises with their template IDs
        exercises = [
            {
                "exercise_template_id": "C6272009",  # Deadlift (Barbell)
                "notes": "Focus on form and depth",
            },
            {
                "exercise_template_id": "79D0BB3A",  # Bench Press (Barbell)
                "notes": "Control the descent",
            },
            {
                "exercise_template_id": "55E6546F",  # Bent Over Row (Barbell)
                "notes": "Keep back straight",
            },
            {
                "exercise_template_id": "3BC06AD3",  # 21s Bicep Curl
                "notes": "Full range of motion",
            },
            {
                "exercise_template_id": "A1B2C3D4",  # Squat (Barbell)
                "notes": "Maintain proper form",
            },
        ]

        # Create workout data
        workout_data = {
            "workout": {
                "title": f"Full Body Workout - {workout_date.strftime('%Y-%m-%d')}",
                "description": "Full body strength training session",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "is_private": False,
                "exercises": [],
            }
        }

        # Add exercises with progressive weights/reps
        for exercise in exercises:
            # Create progressive sets
            sets = []
            for _ in range(random.randint(3, 5)):  # 3-5 sets per exercise
                weight = random.randint(20, 100)
                reps = random.randint(8, 12)
                sets.append(
                    {
                        "type": "normal",
                        "weight_kg": round(weight, 1),
                        "reps": reps,
                        "distance_meters": None,
                        "duration_seconds": None,
                        "custom_metric": None,
                        "rpe": random.randint(6, 9),
                    }
                )

            workout_data["workout"]["exercises"].append(
                {
                    "exercise_template_id": exercise["exercise_template_id"],
                    "superset_id": None,
                    "notes": exercise.get("notes", ""),
                    "sets": sets,
                }
            )

        # Create the workout in Hevy
        workout_id = hevy_api.create_workout(workout_data)
        if workout_id:
            logger.info(f"Created workout with ID: {workout_id}")
            return True
        else:
            logger.error("Failed to create workout")
            return False

    except Exception as e:
        logger.error(f"Error creating workout: {str(e)}")
        return False


def seed_recent_workouts(user_id: str, api_key: str, days: int = 30) -> None:
    """Seed recent workout history for a user.

    Args:
        user_id: User ID to seed history for
        api_key: Hevy API key
        days: Number of days of history to create
    """
    try:
        # Initialize services
        hevy_api = HevyAPI(api_key, is_encrypted=False)

        # Create workouts for the past days
        workouts_created = 0
        for day in range(days):
            # Calculate workout date
            workout_date = datetime.now(timezone.utc) - timedelta(days=day)

            # Add some randomness to the time (between 8 AM and 8 PM)
            workout_date = workout_date.replace(
                hour=random.randint(8, 20),
                minute=random.randint(0, 59),
            )

            # Create the workout
            if create_workout(hevy_api, workout_date):
                workouts_created += 1

        logger.info(
            f"Successfully created {workouts_created} workouts in the past {days} days"
        )

    except Exception as e:
        logger.error(f"Error seeding workout history: {str(e)}")


if __name__ == "__main__":
    # Get test user data
    test_user = get_test_user()
    if not test_user:
        logger.error("Failed to get test user data")
        exit(1)

    # Seed recent workout history for the test user
    seed_recent_workouts(test_user.id, test_user.hevy_api_key)
