#!/usr/bin/env python3
"""
Seed workout history script for staging deployment.
Creates realistic workout history for the past 30 days for a test user.
"""

import json
import logging
import os
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

# Add the parent directory to the path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.database import Database
from app.models.user import FitnessGoal, Sex, UnitSystem, UserProfile

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Common exercises with realistic data
EXERCISES = {
    # Chest exercises
    "bench_press": {
        "id": "50DFDFAB",
        "title": "Bench Press",
        "muscle_groups": [
            {"name": "chest", "is_primary": True},
            {"name": "triceps", "is_primary": False},
            {"name": "shoulders", "is_primary": False},
        ],
        "equipment": [{"name": "barbell"}],
        "base_weight": 60,  # kg
        "progression": 2.5,  # kg per week
        "rep_range": (6, 10),
    },
    "incline_dumbbell_press": {
        "id": "incline_db_press_001",
        "title": "Incline Dumbbell Press",
        "muscle_groups": [
            {"name": "chest", "is_primary": True},
            {"name": "shoulders", "is_primary": False},
        ],
        "equipment": [{"name": "dumbbell"}],
        "base_weight": 25,  # kg per dumbbell
        "progression": 1.25,
        "rep_range": (8, 12),
    },
    "push_ups": {
        "id": "19372ABC",
        "title": "Push Up",
        "muscle_groups": [
            {"name": "chest", "is_primary": True},
            {"name": "triceps", "is_primary": False},
        ],
        "equipment": [{"name": "bodyweight"}],
        "base_weight": 0,
        "progression": 0,
        "rep_range": (12, 20),
    },
    # Back exercises
    "deadlift": {
        "id": "93472AC1",
        "title": "Deadlift",
        "muscle_groups": [
            {"name": "back", "is_primary": True},
            {"name": "legs", "is_primary": False},
            {"name": "core", "is_primary": False},
        ],
        "equipment": [{"name": "barbell"}],
        "base_weight": 80,
        "progression": 2.5,
        "rep_range": (5, 8),
    },
    "pull_ups": {
        "id": "7C50F118",
        "title": "Pull Up",
        "muscle_groups": [
            {"name": "back", "is_primary": True},
            {"name": "biceps", "is_primary": False},
        ],
        "equipment": [{"name": "bodyweight"}],
        "base_weight": 0,
        "progression": 0,
        "rep_range": (6, 12),
    },
    "lat_pulldown": {
        "id": "D2387AB1",
        "title": "Lat Pulldown (Cable)",
        "muscle_groups": [
            {"name": "back", "is_primary": True},
            {"name": "biceps", "is_primary": False},
        ],
        "equipment": [{"name": "cable"}],
        "base_weight": 45,
        "progression": 2.5,
        "rep_range": (8, 12),
    },
    "barbell_row": {
        "id": "barbell_row_001",
        "title": "Barbell Row",
        "muscle_groups": [
            {"name": "back", "is_primary": True},
            {"name": "biceps", "is_primary": False},
        ],
        "equipment": [{"name": "barbell"}],
        "base_weight": 50,
        "progression": 2.5,
        "rep_range": (8, 10),
    },
    # Leg exercises
    "squat": {
        "id": "6622E5A0",
        "title": "Squat",
        "muscle_groups": [
            {"name": "legs", "is_primary": True},
            {"name": "glutes", "is_primary": False},
            {"name": "core", "is_primary": False},
        ],
        "equipment": [{"name": "barbell"}],
        "base_weight": 70,
        "progression": 2.5,
        "rep_range": (6, 10),
    },
    "leg_press": {
        "id": "3FD83744",
        "title": "Leg Press",
        "muscle_groups": [
            {"name": "legs", "is_primary": True},
            {"name": "glutes", "is_primary": False},
        ],
        "equipment": [{"name": "machine"}],
        "base_weight": 120,
        "progression": 5,
        "rep_range": (10, 15),
    },
    "leg_curl": {
        "id": "6120CAAB",
        "title": "Leg Curl",
        "muscle_groups": [{"name": "hamstrings", "is_primary": True}],
        "equipment": [{"name": "machine"}],
        "base_weight": 35,
        "progression": 2.5,
        "rep_range": (10, 15),
    },
    "leg_extension": {
        "id": "629AE73D",
        "title": "Leg Extension",
        "muscle_groups": [{"name": "quadriceps", "is_primary": True}],
        "equipment": [{"name": "machine"}],
        "base_weight": 40,
        "progression": 2.5,
        "rep_range": (12, 15),
    },
    # Shoulder exercises
    "overhead_press": {
        "id": "073032BB",
        "title": "Overhead Press",
        "muscle_groups": [
            {"name": "shoulders", "is_primary": True},
            {"name": "triceps", "is_primary": False},
        ],
        "equipment": [{"name": "barbell"}],
        "base_weight": 40,
        "progression": 1.25,
        "rep_range": (6, 10),
    },
    "lateral_raise": {
        "id": "DE68C825",
        "title": "Lateral Raise",
        "muscle_groups": [{"name": "shoulders", "is_primary": True}],
        "equipment": [{"name": "dumbbell"}],
        "base_weight": 8,
        "progression": 1.25,
        "rep_range": (12, 15),
    },
    # Arm exercises
    "bicep_curl": {
        "id": "01A35BF9",
        "title": "Bicep Curl",
        "muscle_groups": [{"name": "biceps", "is_primary": True}],
        "equipment": [{"name": "dumbbell"}],
        "base_weight": 12,
        "progression": 1.25,
        "rep_range": (10, 15),
    },
    "tricep_dips": {
        "id": "tricep_dips_001",
        "title": "Tricep Dips",
        "muscle_groups": [{"name": "triceps", "is_primary": True}],
        "equipment": [{"name": "bodyweight"}],
        "base_weight": 0,
        "progression": 0,
        "rep_range": (8, 15),
    },
    # Core exercises
    "plank": {
        "id": "E3EDA509",
        "title": "Plank",
        "muscle_groups": [{"name": "core", "is_primary": True}],
        "equipment": [{"name": "bodyweight"}],
        "base_weight": 0,
        "progression": 0,
        "rep_range": (30, 60),  # seconds
        "duration_based": True,
    },
    "russian_twists": {
        "id": "2982AA23",
        "title": "Russian Twists",
        "muscle_groups": [
            {"name": "core", "is_primary": True},
            {"name": "obliques", "is_primary": False},
        ],
        "equipment": [{"name": "bodyweight"}],
        "base_weight": 0,
        "progression": 0,
        "rep_range": (20, 30),
    },
    # Cardio exercises
    "treadmill": {
        "id": "243710DE",
        "title": "Treadmill",
        "muscle_groups": [{"name": "cardio", "is_primary": True}],
        "equipment": [{"name": "cardio"}],
        "base_weight": 0,
        "progression": 0,
        "rep_range": (15, 30),  # minutes
        "duration_based": True,
    },
    "stationary_bike": {
        "id": "stationary_bike_001",
        "title": "Stationary Bike",
        "muscle_groups": [{"name": "cardio", "is_primary": True}],
        "equipment": [{"name": "cardio"}],
        "base_weight": 0,
        "progression": 0,
        "rep_range": (20, 40),  # minutes
        "duration_based": True,
    },
}

# Workout splits and patterns
WORKOUT_SPLITS = {
    "upper_lower": {
        "days": ["upper", "lower", "upper", "lower"],
        "exercises": {
            "upper": [
                "bench_press",
                "barbell_row",
                "overhead_press",
                "lat_pulldown",
                "bicep_curl",
                "tricep_dips",
            ],
            "lower": [
                "squat",
                "deadlift",
                "leg_press",
                "leg_curl",
                "leg_extension",
                "plank",
            ],
        },
    },
    "push_pull_legs": {
        "days": ["push", "pull", "legs", "push", "pull", "legs"],
        "exercises": {
            "push": [
                "bench_press",
                "incline_dumbbell_press",
                "overhead_press",
                "lateral_raise",
                "tricep_dips",
            ],
            "pull": [
                "deadlift",
                "pull_ups",
                "lat_pulldown",
                "barbell_row",
                "bicep_curl",
            ],
            "legs": [
                "squat",
                "leg_press",
                "leg_curl",
                "leg_extension",
                "plank",
                "russian_twists",
            ],
        },
    },
    "full_body": {
        "days": ["full", "full", "full"],
        "exercises": {
            "full": [
                "squat",
                "bench_press",
                "barbell_row",
                "overhead_press",
                "deadlift",
                "plank",
            ]
        },
    },
}


class WorkoutSeeder:
    """Generate realistic workout history for a test user."""

    def __init__(self, db: Database):
        self.db = db

    def create_test_user(self) -> str:
        """Create or find a test user for seeding data."""
        username = "test_user_staging"

        # Check if user already exists
        existing_user = self.db.get_user_by_username(username)
        if existing_user:
            logger.info(
                f"Test user {username} already exists with ID: {existing_user['_id']}"
            )
            return existing_user["_id"]

        # Create new test user
        user = UserProfile.create_user(
            username=username,
            email="test@staging.formava.com",
            password="test_password_123",
            height_cm=175,
            weight_kg=75,
            sex=Sex.MALE,
            age=28,
            fitness_goals=[FitnessGoal.STRENGTH, FitnessGoal.MUSCLE_GAIN],
            experience_level="intermediate",
            preferred_workout_days=4,
            preferred_workout_duration=75,
            preferred_units=UnitSystem.IMPERIAL,
        )

        user_dict = user.to_dict()
        user_id, _ = self.db.save_document(user_dict)
        logger.info(f"Created test user {username} with ID: {user_id}")
        return user_id

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
        is_duration_based = exercise.get("duration_based", False)

        # Number of sets (3-4 for most exercises)
        num_sets = random.choice([3, 3, 4])  # Bias toward 3 sets

        sets = []
        weight = self.calculate_exercise_weight(exercise_name, week_number)

        for i in range(num_sets):
            if is_duration_based:
                # Duration-based exercise (plank, cardio)
                duration = random.randint(rep_range[0], rep_range[1])
                if exercise_name in ["plank"]:
                    # Plank in seconds
                    sets.append(
                        {
                            "type": "normal",
                            "weight_kg": None,
                            "reps": None,
                            "duration_seconds": duration,
                            "distance_meters": None,
                            "custom_metric": None,
                            "rpe": random.choice(
                                [None, None, 6, 7, 8]
                            ),  # Sometimes add RPE
                        }
                    )
                else:
                    # Cardio in minutes -> convert to seconds
                    sets.append(
                        {
                            "type": "normal",
                            "weight_kg": None,
                            "reps": None,
                            "duration_seconds": duration * 60,
                            "distance_meters": None,
                            "custom_metric": None,
                            "rpe": random.choice([None, None, 5, 6, 7]),
                        }
                    )
            else:
                # Rep-based exercise
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
                        "custom_metric": None,
                        "rpe": random.choice(
                            [None, None, 6, 7, 8, 9]
                        ),  # Sometimes add RPE
                    }
                )

        return sets

    def generate_workout(
        self, user_id: str, date: datetime, workout_type: str, week_number: int
    ) -> Dict:
        """Generate a complete workout for a given date and type."""
        split = WORKOUT_SPLITS["upper_lower"]  # Use upper/lower split
        exercises_for_type = split["exercises"][workout_type]

        # Select 4-6 exercises for the workout
        selected_exercises = random.sample(exercises_for_type, random.randint(4, 6))

        # Add occasional cardio
        if random.random() < 0.3:  # 30% chance
            cardio_exercise = random.choice(["treadmill", "stationary_bike"])
            selected_exercises.append(cardio_exercise)

        workout_exercises = []
        for exercise_name in selected_exercises:
            exercise_data = EXERCISES[exercise_name]

            sets = self.generate_sets(exercise_name, week_number)

            # Generate occasional notes
            notes = None
            if random.random() < 0.2:  # 20% chance of notes
                notes_options = [
                    "Felt strong today",
                    "Form was on point",
                    "Challenging but good",
                    "Increased weight from last time",
                    "Good pump",
                    "Felt tired but pushed through",
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

        # Calculate workout duration (45-90 minutes)
        base_duration = 45 + (len(selected_exercises) * 8)  # 8 minutes per exercise
        duration_minutes = random.randint(base_duration - 10, base_duration + 15)

        start_time = date.replace(
            hour=random.randint(7, 19),  # 7 AM to 7 PM
            minute=random.choice([0, 15, 30, 45]),
            second=0,
            microsecond=0,
        )
        end_time = start_time + timedelta(minutes=duration_minutes)

        # Generate workout titles with some variety and emojis
        title_templates = [
            f"{workout_type.title()} Body Day 💪",
            f"{workout_type.title()} Body Workout 🔥",
            f"{workout_type.title()} Training Session",
            f"Crushing {workout_type.title()} Body 💯",
            f"{workout_type.title()} Body Focus",
            f"Strong {workout_type.title()} Day 🏋️",
        ]
        workout_title = random.choice(title_templates)

        # Generate workout descriptions with variety
        descriptions = [
            f"Solid {workout_type} session focusing on strength",
            f"High intensity {workout_type} workout",
            f"Medium intensity {workout_type} day",
            f"Progressive overload {workout_type} training",
            f"Focused {workout_type} development session",
            f"Quality {workout_type} work today",
        ]
        description = random.choice(descriptions)

        # Return in Hevy API format structure
        return {
            "workout": {
                "title": workout_title,
                "description": description,
                "start_time": start_time.isoformat().replace("+00:00", "Z"),
                "end_time": end_time.isoformat().replace("+00:00", "Z"),
                "is_private": False,
                "exercises": workout_exercises,
            },
            # Additional fields for our database storage
            "_metadata": {
                # Don't generate primary ID - let database handle it
                # Only include hevy_id for external reference tracking
                "hevy_id": f"seed_{uuid.uuid4().hex[:12]}",  # For duplicate prevention only
                "user_id": user_id,
                "duration_minutes": duration_minutes,
                "exercise_count": len(workout_exercises),
                "created_at": start_time.isoformat(),
                "updated_at": start_time.isoformat(),
                "type": "workout",
            },
        }

    def seed_workout_history(self, user_id: str, days: int = 30) -> List[str]:
        """Generate workout history for the specified number of days."""
        logger.info(f"Seeding {days} days of workout history for user {user_id}")

        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        # Generate workout schedule (4 days per week)
        workout_days = []
        current_date = start_date
        workout_pattern = ["upper", "lower", "upper", "lower"]
        pattern_index = 0

        while current_date <= end_date:
            # Skip some days to simulate rest days
            if current_date.weekday() not in [6]:  # Skip Sundays mostly
                if random.random() < 0.6:  # 60% chance of working out on non-Sunday
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
                # Flatten the workout structure for database storage
                # Combine the workout data with metadata
                workout_doc = {
                    **workout["workout"],  # Hevy API format fields
                    **workout["_metadata"],  # Our metadata fields
                }

                workout_id = self.db.save_workout(workout_doc, user_id=user_id)
                workout_ids.append(workout_id)
                logger.info(
                    f"Created workout: {workout['workout']['title']} on {workout_day['date'].strftime('%Y-%m-%d')}"
                )
            except Exception as e:
                logger.error(f"Error saving workout: {e}")

        logger.info(f"Successfully created {len(workout_ids)} workouts")
        return workout_ids

    def save_exercises_to_db(self):
        """Save exercise templates to the database."""
        logger.info("Saving exercise templates to database")

        exercises_data = []
        for exercise_name, exercise_data in EXERCISES.items():
            exercise_doc = {
                "id": exercise_data["id"],
                "title": exercise_data["title"],
                "muscle_groups": exercise_data["muscle_groups"],
                "equipment": exercise_data["equipment"],
                "type": "exercise",
                "is_custom": False,
                "exercise_template_id": exercise_data["id"],
            }
            exercises_data.append(exercise_doc)

        # Save exercises using the database method
        self.db.save_exercises(exercises_data)
        logger.info(f"Saved {len(exercises_data)} exercise templates")


def main():
    """Main function to run the seeding script."""
    logger.info("Starting workout history seeding script")

    # Verify we're in staging environment
    env = os.getenv("ENV", "development")
    if env == "production":
        logger.error("Cannot run seeding script in production environment!")
        logger.error("This script is intended for staging/development only.")
        sys.exit(1)
    elif env == "staging":
        logger.info("Running in staging environment - this is the intended environment")
    else:
        logger.warning(
            f"Running in {env} environment - this script is intended for staging"
        )

    # Initialize database connection
    try:
        db = Database()
        logger.info("Successfully connected to database")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        sys.exit(1)

    # Initialize seeder
    seeder = WorkoutSeeder(db)

    # Save exercise templates first
    seeder.save_exercises_to_db()

    # Create or find test user
    user_id = seeder.create_test_user()

    # Generate workout history
    workout_ids = seeder.seed_workout_history(user_id, days=30)

    logger.info(
        f"Seeding complete! Created {len(workout_ids)} workouts for user {user_id}"
    )
    logger.info("Test user credentials:")
    logger.info("  Username: test_user_staging")
    logger.info("  Password: test_password_123")


if __name__ == "__main__":
    main()
