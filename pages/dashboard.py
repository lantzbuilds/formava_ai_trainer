"""
Dashboard page for the AI Personal Trainer application.
"""

import logging
from datetime import datetime, timezone

import streamlit as st

from config.database import Database
from models.user import UserProfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database connection
db = Database()


def dashboard_page():
    """Display the dashboard page."""
    st.title("Dashboard")

    # Get user document from database
    user_doc = db.get_document(st.session_state.user_id)
    if not user_doc:
        st.error("User profile not found")
        return

    # Create UserProfile instance
    user = UserProfile(**user_doc)

    # Display welcome message
    st.write(f"Welcome back, {user.username}!")

    # Display user's fitness goals
    st.subheader("Your Fitness Goals")
    for goal in user.fitness_goals:
        st.write(f"- {goal.value}")

    # Display workout schedule
    st.subheader("Your Workout Schedule")
    st.write(f"You plan to work out {user.preferred_workout_days} days per week")
    st.write(
        f"Your preferred workout duration is {user.preferred_workout_duration} minutes"
    )

    # Display active injuries if any
    active_injuries = [i for i in user.injuries if i["is_active"]]
    if active_injuries:
        st.subheader("Active Injuries")
        for injury in active_injuries:
            st.warning(
                f"**{injury['description']}** ({injury['body_part']}) - {injury['severity']} severity"
            )

    # Display Hevy API integration status
    st.subheader("Hevy Integration")
    if user.hevy_api_key:
        st.success("Hevy API key is configured")
        # TODO: Add Hevy workout data display
    else:
        st.warning("Hevy API key is not configured")
        st.write(
            "Configure your Hevy API key in the Profile page to enable workout tracking"
        )

    # TODO: Add workout history and progress tracking
    st.subheader("Workout History")
    st.info("Workout history tracking coming soon!")

    # TODO: Add progress tracking
    st.subheader("Progress Tracking")
    st.info("Progress tracking coming soon!")
