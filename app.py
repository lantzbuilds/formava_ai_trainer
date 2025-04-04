"""
Main application file for the AI Personal Trainer.
"""

import logging
import os
from datetime import datetime, timedelta, timezone

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from config.database import Database
from models.user import FitnessGoal, Injury, InjurySeverity, Sex, UserProfile
from pages.ai_recommendations import ai_recommendations_page
from pages.dashboard import dashboard_page
from pages.login import login_page
from pages.profile import profile_page
from pages.register import register_page
from pages.sync_hevy import sync_hevy_page
from pages.workout_history import workout_history_page
from pages.workout_preferences import workout_preferences_page
from services.hevy_api import HevyAPI
from services.openai_service import OpenAIService
from utils.crypto import decrypt_api_key, encrypt_api_key
from utils.units import (
    cm_to_inches,
    format_height_cm,
    format_weight_kg,
    inches_to_cm,
    kg_to_lbs,
    lbs_to_kg,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize database connection
db = Database()


# Sidebar navigation
def sidebar():
    if st.session_state.user_id:
        # User is logged in
        st.sidebar.write(f"Welcome, {st.session_state.username}!")
        page = st.sidebar.radio(
            "Navigation",
            [
                "Dashboard",
                "Workout History",
                "AI Recommendations",
                "Sync Hevy",
                "Workout Preferences",
                "Profile",
            ],
        )
        if st.sidebar.button("Logout"):
            st.session_state.user_id = None
            st.session_state.username = None
            st.rerun()
    else:
        # User is not logged in
        page = st.sidebar.radio(
            "Navigation",
            ["Login", "Register"],
        )
    return page


# Main app
def main():
    # Configure the page
    st.set_page_config(
        page_title="AI Personal Trainer",
        page_icon="💪",
        layout="wide",
    )

    # Initialize session state
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "username" not in st.session_state:
        st.session_state.username = None

    page = sidebar()

    # Display the selected page
    if page == "Login":
        login_page()
    elif page == "Register":
        register_page()
    elif page == "Dashboard":
        dashboard_page()
    elif page == "Workout History":
        workout_history_page()
    elif page == "AI Recommendations":
        ai_recommendations_page()
    elif page == "Profile":
        profile_page()
    elif page == "Sync Hevy":
        sync_hevy_page()
    elif page == "Workout Preferences":
        workout_preferences_page()


if __name__ == "__main__":
    main()
