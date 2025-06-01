"""
Login page for the AI Personal Trainer application.
"""

import logging
from datetime import datetime, timedelta, timezone

import streamlit as st

from config.database import Database
from models.user import UserProfile
from services.hevy_api import HevyAPI
from services.vector_store import ExerciseVectorStore
from utils.crypto import decrypt_api_key

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database connection
db = Database()


def initialize_user_data(user: UserProfile):
    """
    Initialize user data after login, including fetching and vectorizing workout history
    and ensuring all exercises are vectorized.

    Args:
        user: UserProfile instance
    """
    try:
        # Initialize vector store
        vector_store = ExerciseVectorStore()

        # Get all exercises (standard and custom)
        exercises = db.get_exercises(user_id=user.id, include_custom=True)
        if exercises:
            # Check if we need to add any exercises
            exercises_to_add = []
            for exercise in exercises:
                # Check if exercise exists in vector store
                existing = vector_store.search_exercises_by_title(
                    exercise.get("title", "")
                )
                if not existing:
                    exercises_to_add.append(exercise)

            if exercises_to_add:
                logger.info(f"Found {len(exercises_to_add)} new exercises to vectorize")
                # Add only new exercises to vector store
                vector_store.add_exercises(exercises_to_add)
                logger.info("Successfully vectorized new exercises")
            else:
                logger.info("All exercises are already vectorized")

        # If user has Hevy API key, fetch and vectorize workout history
        if user.hevy_api_key:
            # Initialize date variables outside the try block
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=30)

            try:
                # Decrypt API key
                api_key = decrypt_api_key(user.hevy_api_key)
                hevy_api = HevyAPI(api_key, is_encrypted=False)

                # Get workouts from database
                workouts = db.get_user_workout_history(user.id, start_date, end_date)

                if workouts:
                    logger.info(f"Found {len(workouts)} workouts to vectorize")
                    # Add workouts to vector store
                    vector_store.add_workout_history(workouts)
                    logger.info("Successfully vectorized workout history")
                else:
                    logger.info("No workouts found in database, fetching from Hevy API")
                    # Fetch workouts from Hevy API
                    workouts = hevy_api.get_workouts(start_date, end_date)

                    if workouts:
                        logger.info(f"Found {len(workouts)} workouts from Hevy API")
                        # Save workouts to database
                        for workout in workouts:
                            workout_data = {
                                "hevy_id": workout["id"],
                                "user_id": user.id,
                                "title": workout.get("title", "Untitled Workout"),
                                "description": workout.get("description", ""),
                                "start_time": workout.get("start_time"),
                                "end_time": workout.get("end_time"),
                                "exercises": workout.get("exercises", []),
                                "exercise_count": len(workout.get("exercises", [])),
                            }
                            db.save_workout(workout_data)

                        # Add workouts to vector store
                        vector_store.add_workout_history(workouts)
                        logger.info(
                            "Successfully vectorized workout history from Hevy API"
                        )
                    else:
                        logger.info("No workouts found in Hevy API")

            except Exception as e:
                logger.error(f"Error initializing Hevy data: {str(e)}", exc_info=True)
                # Log additional context
                logger.error(f"User ID: {user.id}")
                logger.error(f"Has Hevy API key: {bool(user.hevy_api_key)}")
                logger.error(f"Start date: {start_date}")
                logger.error(f"End date: {end_date}")

    except Exception as e:
        logger.error(f"Error initializing user data: {str(e)}", exc_info=True)


def login_page():
    """Display the login page."""
    st.title("Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

        if submit:
            # Get user from database
            user_doc = db.get_user_by_username(username)
            if user_doc:
                # Create UserProfile instance from document
                user = UserProfile(**user_doc)
                # Verify password
                if user.verify_password(password):
                    # Store the document ID, not the user ID
                    st.session_state.user_id = user_doc["_id"]
                    st.session_state.username = username

                    # Initialize user data
                    initialize_user_data(user)

                    st.rerun()
                else:
                    st.error("Invalid username or password")
            else:
                st.error("Invalid username or password")
