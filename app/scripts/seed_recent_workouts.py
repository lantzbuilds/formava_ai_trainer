#!/usr/bin/env python3
"""
Script to seed recent workout history for the test user.
"""

import json
import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List

import requests
from config.database import Database
from models.user import UserProfile
from services.hevy_api import HevyAPI
from services.vector_store import ExerciseVectorStore

# Configure logging
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


def get_exercise_templates() -> Dict[str, str]:
    """Get valid exercise templates from our database.

    Returns:
        Dictionary mapping exercise names to their template IDs
    """
    try:
        # Initialize database and vector store
        db = Database()
        vector_store = ExerciseVectorStore()

        # Get all exercises from the database
        exercises = db.get_exercises(include_custom=True)
        logger.info(f"Found {len(exercises)} exercises in the database")

        # Create a mapping of exercise names to their template IDs
        exercise_map = {}
        for exercise in exercises:
            exercise_map[exercise["title"].lower()] = exercise["id"]

        logger.info(f"Created mapping with {len(exercise_map)} exercise templates")
        return exercise_map
    except Exception as e:
        logger.error(f"Error fetching exercise templates: {str(e)}")
        return {}


def create_workout(
    hevy_api: HevyAPI,
    workout_date: datetime,
    day_number: int,
    exercise_map: Dict[str, str],
) -> bool:
    """Create a workout in Hevy.

    Args:
        hevy_api: HevyAPI instance
        workout_date: Date for the workout
        day_number: Number of days ago (0 = today, 1 = yesterday, etc.)
        exercise_map: Dictionary mapping exercise names to their template IDs

    Returns:
        True if successful, False otherwise
    """
    try:
        # Calculate workout duration (30-60 minutes)
        duration_minutes = random.randint(30, 60)
        start_time = workout_date
        end_time = start_time + timedelta(minutes=duration_minutes)

        # Sample exercises with their base weights
        exercises = [
            {
                "name": "deadlift (barbell)",
                "notes": "Focus on form and depth",
                "base_weight": 60,  # Starting weight in kg
                "weight_increment": 2.5,  # Weight increase per week
                "base_reps": 8,
                "reps_increment": 1,  # Rep increase per week
            },
            {
                "name": "bench press (barbell)",
                "notes": "Control the descent",
                "base_weight": 40,
                "weight_increment": 2.5,
                "base_reps": 8,
                "reps_increment": 1,
            },
            {
                "name": "bent over row (barbell)",
                "notes": "Keep back straight",
                "base_weight": 35,
                "weight_increment": 2.5,
                "base_reps": 10,
                "reps_increment": 1,
            },
            {
                "name": "bicep curl (dumbbell)",
                "notes": "Full range of motion",
                "base_weight": 15,
                "weight_increment": 1.25,
                "base_reps": 12,
                "reps_increment": 1,
            },
            {
                "name": "squat (barbell)",
                "notes": "Maintain proper form",
                "base_weight": 50,
                "weight_increment": 2.5,
                "base_reps": 8,
                "reps_increment": 1,
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

        # Calculate weeks of progression
        weeks_progressed = day_number // 7

        # Add exercises with progressive weights/reps
        for exercise in exercises:
            # Get the exercise template ID
            exercise_name = exercise["name"].lower()
            if exercise_name not in exercise_map:
                logger.warning(f"Exercise template not found: {exercise_name}")
                continue

            # Calculate progressive weight and reps
            current_weight = exercise["base_weight"] + (
                weeks_progressed * exercise["weight_increment"]
            )
            current_reps = exercise["base_reps"] + (
                weeks_progressed * exercise["reps_increment"]
            )

            # Create progressive sets
            sets = []
            for set_num in range(4):  # Always 4 sets for consistency
                # Add slight variation to weight and reps within the workout
                # but maintain progression over time
                set_weight = current_weight * (
                    1 + (set_num * 0.05)
                )  # 5% increase per set
                set_reps = current_reps - (set_num * 1)  # Decrease reps by 1 per set

                # Ensure minimum values
                set_weight = max(20, set_weight)
                set_reps = max(5, set_reps)

                sets.append(
                    {
                        "type": "normal",
                        "weight_kg": round(set_weight, 1),
                        "reps": int(set_reps),
                        "distance_meters": None,
                        "duration_seconds": None,
                        "custom_metric": None,
                        "rpe": 7 + (set_num // 2),  # RPE increases with set number
                    }
                )

            workout_data["workout"]["exercises"].append(
                {
                    "exercise_template_id": exercise_map[exercise_name],
                    "superset_id": None,
                    "notes": exercise.get("notes", ""),
                    "sets": sets,
                }
            )

        # Log the workout data before sending
        logger.info("Creating workout with data:")
        logger.info(json.dumps(workout_data, indent=2))

        # Create workout in Hevy with detailed error logging
        try:
            # Get the raw response from the API
            url = f"{hevy_api.base_url}/workouts"
            response = requests.post(url, headers=hevy_api.headers, json=workout_data)

            # Log the response status and content
            logger.info(f"API Response Status: {response.status_code}")
            logger.info(f"API Response Content: {response.text}")

            # Check if the request was successful
            if response.status_code == 200 or response.status_code == 201:
                # Extract workout ID from the response
                response_data = response.json()
                if (
                    "workout" in response_data
                    and isinstance(response_data["workout"], list)
                    and len(response_data["workout"]) > 0
                ):
                    workout_id = response_data["workout"][0].get("id")
                    logger.info(f"Created workout with ID: {workout_id}")
                    return True
                else:
                    logger.error("Failed to extract workout ID from response")
                    return False
            else:
                logger.error(
                    f"Failed to create workout. Status code: {response.status_code}"
                )
                logger.error(f"Error response: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Exception while creating workout: {str(e)}")
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
        hevy_api = HevyAPI(api_key, is_encrypted=True)

        # Get valid exercise templates
        exercise_map = get_exercise_templates()
        if not exercise_map:
            logger.error("Failed to get exercise templates")
            return

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
            if create_workout(hevy_api, workout_date, day, exercise_map):
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
