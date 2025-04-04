"""
Hevy sync page for the AI Personal Trainer application.
"""

import logging
from datetime import datetime, timedelta, timezone

import streamlit as st

from config.database import Database
from models.user import UserProfile
from services.hevy_api import HevyAPI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
db = Database()


def sync_hevy_page():
    """Display the Hevy sync page."""
    st.title("Sync Hevy Workouts")

    # Get user document from database
    user_doc = db.get_document(st.session_state.user_id)
    if not user_doc:
        st.error("User profile not found")
        return

    # Create UserProfile instance
    user = UserProfile(**user_doc)

    # Check if Hevy API key is configured
    if not user.hevy_api_key:
        st.warning("Hevy API key is not configured")
        st.write("Please configure your Hevy API key in the Profile page first.")
        return

    # Display last sync time
    if "last_hevy_sync" in user_doc:
        last_sync = datetime.fromisoformat(user_doc["last_hevy_sync"])
        st.write(f"**Last synced:** {last_sync.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        st.write("**Last synced:** Never")

    # Sync options
    sync_option = st.radio(
        "What would you like to sync?",
        ["Workouts Only", "Base Exercises Only", "Custom Exercises Only", "Everything"],
    )

    # Sync button
    if st.button("Sync"):
        with st.spinner("Syncing from Hevy..."):
            try:
                # Initialize Hevy API with the user's API key
                hevy_api = HevyAPI(user.hevy_api_key)

                # Sync base exercises if selected
                if sync_option in ["Base Exercises Only", "Everything"]:
                    st.write("Syncing base exercises...")
                    base_exercise_list = hevy_api.get_all_exercises(
                        include_custom=False
                    )
                    if base_exercise_list.exercises:
                        # Convert to dictionary format for database storage
                        exercises_data = [
                            exercise.model_dump()
                            for exercise in base_exercise_list.exercises
                        ]
                        db.save_exercises(
                            exercises_data
                        )  # No user_id for base exercises
                        st.success(
                            f"Successfully synced {len(base_exercise_list.exercises)} base exercises!"
                        )
                    else:
                        st.info("No base exercises found to sync.")

                # Sync custom exercises if selected
                if sync_option in ["Custom Exercises Only", "Everything"]:
                    st.write("Syncing custom exercises...")
                    custom_exercise_list = hevy_api.get_all_exercises(
                        include_custom=True
                    )
                    if custom_exercise_list.exercises:
                        # Filter to only include custom exercises
                        custom_exercises = [
                            exercise
                            for exercise in custom_exercise_list.exercises
                            if exercise.is_custom
                        ]
                        if custom_exercises:
                            # Convert to dictionary format for database storage
                            exercises_data = [
                                exercise.model_dump() for exercise in custom_exercises
                            ]
                            db.save_exercises(
                                exercises_data, user_id=st.session_state.user_id
                            )
                            st.success(
                                f"Successfully synced {len(custom_exercises)} custom exercises!"
                            )
                        else:
                            st.info("No custom exercises found to sync.")
                    else:
                        st.info("No custom exercises found to sync.")

                # Sync workouts if selected
                if sync_option in ["Workouts Only", "Everything"]:
                    st.write("Syncing workouts...")
                    # Get workouts from Hevy
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=30)
                    workouts = hevy_api.get_workouts(
                        start_date,
                        end_date,
                    )

                    if workouts:
                        # Save workouts to database
                        for workout in workouts:
                            db.save_workout(workout)

                        st.success(f"Successfully synced {len(workouts)} workouts!")
                    else:
                        st.info("No new workouts found to sync.")

                # Update last sync time
                user_doc["last_hevy_sync"] = datetime.now(timezone.utc).isoformat()
                db.save_document(user_doc, doc_id=st.session_state.user_id)

            except Exception as e:
                logger.error(f"Error syncing from Hevy: {str(e)}")
                st.error(
                    "Failed to sync from Hevy. Please check your Hevy API key and try again."
                )

    # Display available exercises
    st.subheader("Available Exercises")

    # Get base exercises
    base_exercises = db.get_exercises(include_custom=False)
    st.write(f"**Base exercises available:** {len(base_exercises)}")

    # Get custom exercises for the current user
    custom_exercises = db.get_custom_exercises(st.session_state.user_id)
    st.write(f"**Your custom exercises:** {len(custom_exercises)}")

    # Group exercises by muscle group
    all_exercises = base_exercises + custom_exercises
    if all_exercises:
        muscle_groups = {}
        for exercise in all_exercises:
            for muscle in exercise.get("muscle_groups", []):
                muscle_name = muscle.get("name", "Unknown")
                if muscle_name not in muscle_groups:
                    muscle_groups[muscle_name] = []
                muscle_groups[muscle_name].append(exercise.get("name", "Unknown"))

        # Display muscle groups and exercise counts
        st.write("**Exercises by muscle group:**")
        for muscle, exercise_list in muscle_groups.items():
            st.write(f"- {muscle}: {len(exercise_list)} exercises")
    else:
        st.write(
            "**No exercises available. Please sync with Hevy to get exercise data.**"
        )

    # Display recent synced workouts
    st.subheader("Recent Synced Workouts")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    workouts = db.get_user_workout_history(
        st.session_state.user_id,
        start_date,
        end_date,
    )

    if workouts:
        for workout in workouts:
            with st.expander(f"{workout['title']} - {workout['start_time']}"):
                st.write(
                    f"**Description:** {workout.get('description', 'No description')}"
                )
                st.write(f"**Exercises:** {workout['exercise_count']}")
                if "duration" in workout:
                    st.write(f"**Duration:** {workout['duration']:.1f} minutes")
    else:
        st.write("No recent workouts found.")
