#!/usr/bin/env python3
"""
Seed script to populate Hevy test account with sample data.
This script creates a sample routine and workout history in Hevy.
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone

import requests

# Add the parent directory to the path so we can import from the project
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import Database
from models.user import UserProfile
from services.hevy_api import HevyAPI
from utils.crypto import encrypt_api_key

# Configure logging
logger = logging.getLogger(__name__)


def get_test_user():
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


def create_sample_routine(hevy_api):
    """Create a sample routine in Hevy."""
    # Sample routine data in Hevy API format using actual exercise IDs
    routine_data = {
        "routine": {
            "title": "Full Body Strength",
            "folder_id": None,
            "notes": "A balanced full-body workout focusing on compound movements",
            "exercises": [
                {
                    "exercise_template_id": "C6272009",  # Deadlift (Barbell)
                    "superset_id": None,
                    "rest_seconds": 90,
                    "notes": "Focus on form and depth",
                    "sets": [
                        {
                            "type": "normal",
                            "weight_kg": None,
                            "reps": 8,
                            "distance_meters": None,
                            "duration_seconds": None,
                            "custom_metric": None,
                        }
                    ],
                },
                {
                    "exercise_template_id": "79D0BB3A",  # Bench Press (Barbell)
                    "superset_id": None,
                    "rest_seconds": 90,
                    "notes": "Control the descent",
                    "sets": [
                        {
                            "type": "normal",
                            "weight_kg": None,
                            "reps": 8,
                            "distance_meters": None,
                            "duration_seconds": None,
                            "custom_metric": None,
                        }
                    ],
                },
                {
                    "exercise_template_id": "55E6546F",  # Bent Over Row (Barbell)
                    "superset_id": None,
                    "rest_seconds": 90,
                    "notes": "Keep back straight",
                    "sets": [
                        {
                            "type": "normal",
                            "weight_kg": None,
                            "reps": 10,
                            "distance_meters": None,
                            "duration_seconds": None,
                            "custom_metric": None,
                        }
                    ],
                },
            ],
        }
    }

    # Log the routine data for debugging
    logger.info(f"Creating routine with data: {json.dumps(routine_data, indent=2)}")

    # Create routine in Hevy with detailed error logging
    try:
        # Get the raw response from the API
        # TODO: Move request to HevyAPI class
        url = f"{hevy_api.base_url}/routines"
        response = requests.post(url, headers=hevy_api.headers, json=routine_data)

        # Log the response status and content
        logger.info(f"API Response Status: {response.status_code}")
        logger.info(f"API Response Content: {response.text}")

        # Check if the request was successful
        if response.status_code == 200 or response.status_code == 201:
            # Extract routine ID from the response
            response_data = response.json()
            if (
                "routine" in response_data
                and isinstance(response_data["routine"], list)
                and len(response_data["routine"]) > 0
            ):
                routine_id = response_data["routine"][0].get("id")
                logger.info(f"Created routine with ID: {routine_id}")
                return routine_id
            else:
                logger.error("Failed to extract routine ID from response")
                return None
        else:
            logger.error(
                f"Failed to create routine. Status code: {response.status_code}"
            )
            logger.error(f"Error response: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Exception while creating routine: {str(e)}")
        return None


def create_sample_workout(hevy_api, routine_id):
    """Create a sample workout from the routine."""
    # Get routine details
    routines = hevy_api.get_routines()
    routine = next((r for r in routines if r.get("id") == routine_id), None)

    if not routine:
        logger.error("Routine not found")
        return None

    # Create workout data in Hevy API format
    now = datetime.now(timezone.utc)
    workout_data = {
        "workout": {
            "title": f"Workout - {routine.get('title', 'Untitled')}",
            "description": "Completed first session of the routine",
            "start_time": (now - timedelta(minutes=60)).isoformat(),
            "end_time": now.isoformat(),
            "is_private": False,
            "exercises": [],
        }
    }

    # Add exercises from routine
    for exercise in routine.get("exercises", []):
        workout_exercise = {
            "exercise_template_id": exercise.get("exercise_template_id"),
            "superset_id": None,
            "notes": exercise.get("notes", ""),
            "sets": [],
        }

        # Add sets
        for set_data in exercise.get("sets", []):
            workout_set = {
                "type": "normal",
                "weight_kg": 60.0,  # Sample weight
                "reps": set_data.get(
                    "reps", 8
                ),  # Use the reps from the routine or default to 8
                "distance_meters": None,
                "duration_seconds": None,
                "custom_metric": None,
                "rpe": None,
            }
            workout_exercise["sets"].append(workout_set)

        workout_data["workout"]["exercises"].append(workout_exercise)

    # Log the workout data for debugging
    logger.info(f"Creating workout with data: {json.dumps(workout_data, indent=2)}")

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
                return workout_id
            else:
                logger.error("Failed to extract workout ID from response")
                return None
        else:
            logger.error(
                f"Failed to create workout. Status code: {response.status_code}"
            )
            logger.error(f"Error response: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Exception while creating workout: {str(e)}")
        return None


def get_or_create_routine(hevy_api, routine_data):
    """Get an existing routine by title or create a new one."""
    # Get all routines
    routines = hevy_api.get_routines()

    # Check if a routine with the same title already exists
    routine_title = routine_data["routine"]["title"]
    existing_routine = next(
        (r for r in routines if r.get("title") == routine_title), None
    )

    if existing_routine:
        logger.info(f"Found existing routine with ID: {existing_routine['id']}")
        return existing_routine["id"]

    # If no existing routine found, create a new one
    try:
        url = f"{hevy_api.base_url}/routines"
        response = requests.post(url, headers=hevy_api.headers, json=routine_data)

        if response.status_code == 200 or response.status_code == 201:
            routine_id = response.json().get("id")
            logger.info(f"Created new routine with ID: {routine_id}")
            return routine_id
        else:
            logger.error(
                f"Failed to create routine. Status code: {response.status_code}"
            )
            logger.error(f"Error response: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Exception while creating routine: {str(e)}")
        return None


def main():
    """Main function to seed Hevy data."""
    # Get test user
    test_user = get_test_user()
    if not test_user:
        return

    # Initialize Hevy API
    hevy_api = HevyAPI(test_user.hevy_api_key)

    # Use option 2: Check for existing routines and create only if needed
    routine_data = {
        "routine": {
            "title": "Full Body Strength",
            "folder_id": None,
            "notes": "A balanced full-body workout focusing on compound movements",
            "exercises": [
                {
                    "exercise_template_id": "C6272009",  # Deadlift (Barbell)
                    "superset_id": None,
                    "rest_seconds": 90,
                    "notes": "Focus on form and depth",
                    "sets": [
                        {
                            "type": "normal",
                            "weight_kg": None,
                            "reps": 8,
                            "distance_meters": None,
                            "duration_seconds": None,
                            "custom_metric": None,
                        }
                    ],
                },
                {
                    "exercise_template_id": "79D0BB3A",  # Bench Press (Barbell)
                    "superset_id": None,
                    "rest_seconds": 90,
                    "notes": "Control the descent",
                    "sets": [
                        {
                            "type": "normal",
                            "weight_kg": None,
                            "reps": 8,
                            "distance_meters": None,
                            "duration_seconds": None,
                            "custom_metric": None,
                        }
                    ],
                },
                {
                    "exercise_template_id": "55E6546F",  # Bent Over Row (Barbell)
                    "superset_id": None,
                    "rest_seconds": 90,
                    "notes": "Keep back straight",
                    "sets": [
                        {
                            "type": "normal",
                            "weight_kg": None,
                            "reps": 10,
                            "distance_meters": None,
                            "duration_seconds": None,
                            "custom_metric": None,
                        }
                    ],
                },
            ],
        }
    }
    routine_id = get_or_create_routine(hevy_api, routine_data)

    if not routine_id:
        return

    # Create sample workout
    workout_id = create_sample_workout(hevy_api, routine_id)
    if not workout_id:
        return

    logger.info("Successfully seeded Hevy data")
    logger.info(f"Routine ID: {routine_id}")
    logger.info(f"Workout ID: {workout_id}")


if __name__ == "__main__":
    main()
