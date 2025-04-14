"""
Workout history page for the AI Personal Trainer application.
"""

import logging
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from config.database import Database
from models.user import UserProfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database connection
db = Database()


@st.cache_data(ttl=0)
def workout_history_page():
    """Display the workout history page."""
    st.title("Workout History")

    # Get user document from database
    user_doc = db.get_document(st.session_state.user_id)
    if not user_doc:
        st.error("User profile not found")
        return

    # Create UserProfile instance
    user = UserProfile(**user_doc)

    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=datetime.now().date() - timedelta(days=30),
        )
    with col2:
        end_date = st.date_input(
            "End Date",
            value=datetime.now().date(),
        )

    # Get user's workouts for the selected date range
    workouts = db.get_user_workout_history(
        st.session_state.user_id,
        datetime.combine(start_date, datetime.min.time()),
        datetime.combine(end_date, datetime.max.time()),
    )

    if workouts:
        # Create a DataFrame for visualization
        workout_data = []
        for workout in workouts:
            workout_data.append(
                {
                    "date": workout["start_time"],
                    "title": workout["title"],
                    "exercises": len(workout.get("exercises", [])),
                    "duration": workout.get("duration", 0),
                }
            )

        df = pd.DataFrame(workout_data)

        # TODO: fix workout frequency display
        # Display workout frequency
        st.subheader("Workout Frequency")
        fig = px.bar(
            df, x="date", y="exercises", title="Workouts in Selected Date Range"
        )
        st.plotly_chart(fig, use_container_width=True)

        # Display recent workouts
        st.subheader("Recent Workouts")
        for workout in workouts[:5]:  # Show last 5 workouts
            with st.expander(f"{workout['title']} - {workout['start_time']}"):
                st.write(
                    f"**Description:** {workout.get('description', 'No description')}"
                )
                st.write(f"**Exercises:** {len(workout.get('exercises', []))}")
                if "duration" in workout:
                    st.write(f"**Duration:** {workout['duration']:.1f} minutes")
    else:
        st.info("No workouts found for the selected date range.")
