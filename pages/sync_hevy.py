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

    # Sync button
    if st.button("Sync Workouts"):
        with st.spinner("Syncing workouts from Hevy..."):
            try:
                # Initialize Hevy API with the user's API key
                hevy_api = HevyAPI(user.hevy_api_key)

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
                        db.save_workout(st.session_state.user_id, workout)

                    # Update last sync time
                    user_doc["last_hevy_sync"] = datetime.now(timezone.utc).isoformat()
                    db.save_document(user_doc, doc_id=st.session_state.user_id)

                    st.success(f"Successfully synced {len(workouts)} workouts!")
                else:
                    st.info("No new workouts found to sync.")
            except Exception as e:
                logger.error(f"Error syncing workouts: {str(e)}")
                st.error(
                    "Failed to sync workouts. Please check your Hevy API key and try again."
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
        st.info("No workouts found in the last 7 days.")
