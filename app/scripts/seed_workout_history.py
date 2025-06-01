"""
Script to seed workout history based on AI-generated routines.
"""

import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from config.database import Database
from models.user import UserProfile
from services.hevy_api import HevyAPI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_test_user() -> Optional[UserProfile]:
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


def get_ai_routine(db: Database, user_id: str) -> Optional[Dict]:
    """Get the most recent AI-generated routine from the database.

    Args:
        db: Database instance
        user_id: User ID to get routines for

    Returns:
        Routine folder data or None if not found
    """
    try:
        # Get all routine folders for the user
        routine_folders = db.get_documents_by_type("routine_folder", user_id=user_id)
        if not routine_folders:
            logger.error("No routine folders found")
            return None

        # Sort by created_at and get the most recent
        latest_folder = max(routine_folders, key=lambda x: x.get("created_at", ""))
        logger.info(f"Found routine folder: {latest_folder['name']}")
        return latest_folder

    except Exception as e:
        logger.error(f"Error getting AI routine: {str(e)}")
        return None


def create_workout_from_routine(
    hevy_api: HevyAPI,
    routine: Dict,
    workout_date: datetime,
    progression_factor: float = 1.0,
) -> bool:
    """Create a workout in Hevy based on a routine.

    Args:
        hevy_api: HevyAPI instance
        routine: Routine data
        workout_date: Date for the workout
        progression_factor: Factor to adjust weights/reps (1.0 = no change)

    Returns:
        True if successful, False otherwise
    """
    try:
        # Calculate workout duration (30-60 minutes)
        duration_minutes = random.randint(30, 60)
        start_time = workout_date
        end_time = start_time + timedelta(minutes=duration_minutes)

        # Create workout data
        workout_data = {
            "workout": {
                "title": routine["hevy_api"]["routine"]["title"],
                "description": f"Workout from {routine['hevy_api']['routine']['title']}",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "is_private": False,
                "exercises": [],
            }
        }

        # Add exercises with progressive weights/reps
        for exercise in routine["hevy_api"]["routine"]["exercises"]:
            # Skip warm-up exercises
            if "warm" in exercise.get("notes", "").lower():
                continue

            # Create progressive sets
            sets = []
            for _ in range(random.randint(3, 5)):  # 3-5 sets per exercise
                weight = random.randint(20, 100) * progression_factor
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


def seed_workout_history(user_id: str, api_key: str, weeks: int = 4) -> None:
    """Seed workout history for a user.

    Args:
        user_id: User ID to seed history for
        api_key: Hevy API key
        weeks: Number of weeks of history to create
    """
    try:
        # Initialize services
        db = Database()
        hevy_api = HevyAPI(api_key)

        # Get an AI-generated routine
        routine_folder = get_ai_routine(db, user_id)
        if not routine_folder:
            logger.error("No AI routine found to base workouts on")
            return

        # Create workouts for each routine in the folder
        for routine in routine_folder["routines"]:
            # Get the day of week from the routine
            day_name = routine["day"].lower()
            day_map = {
                "monday": 0,
                "tuesday": 1,
                "wednesday": 2,
                "thursday": 3,
                "friday": 4,
                "saturday": 5,
                "sunday": 6,
            }
            day_offset = day_map.get(day_name, 0)

            # Create workouts for the past weeks
            for week in range(weeks):
                # Calculate workout date (week * 7 days + day offset)
                days_ago = (weeks - week - 1) * 7 + day_offset
                workout_date = datetime.now(timezone.utc) - timedelta(days=days_ago)

                # Add some randomness to the time (between 8 AM and 8 PM)
                workout_date = workout_date.replace(
                    hour=random.randint(8, 20),
                    minute=random.randint(0, 59),
                )

                # Calculate progression factor (slight improvement each week)
                progression_factor = 1.0 + (week * 0.05)  # 5% improvement per week

                # Create the workout
                create_workout_from_routine(
                    hevy_api=hevy_api,
                    routine=routine,
                    workout_date=workout_date,
                    progression_factor=progression_factor,
                )

        logger.info(f"Successfully seeded {weeks} weeks of workout history")

    except Exception as e:
        logger.error(f"Error seeding workout history: {str(e)}")


if __name__ == "__main__":
    # Get test user data
    test_user = get_test_user()
    if not test_user:
        logger.error("Failed to get test user data")
        exit(1)

    # Seed workout history for the test user
    seed_workout_history(test_user.id, test_user.hevy_api_key)
