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
from pages.routines import routines_page
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

# Configure Streamlit page
st.set_page_config(
    page_title="AI Personal Trainer",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state for user authentication
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = None


def sidebar():
    """
    Render the sidebar navigation.
    """
    with st.sidebar:
        st.title("AI Personal Trainer")

        # Check if user is logged in
        if "user_id" in st.session_state:
            # Navigation options for logged-in users
            selected = st.radio(
                "Navigation",
                [
                    "Dashboard",
                    "Workout History",
                    "AI Recommendations",
                    "Routines",
                    "Sync Hevy",
                    "Profile",
                    "Logout",
                ],
            )

            # Handle navigation
            if selected == "Dashboard":
                dashboard_page()
            elif selected == "Workout History":
                workout_history_page()
            elif selected == "AI Recommendations":
                ai_recommendations_page()
            elif selected == "Routines":
                routines_page()
            elif selected == "Sync Hevy":
                sync_hevy_page()
            elif selected == "Profile":
                profile_page()
            elif selected == "Logout":
                # Clear session state
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.experimental_rerun()
        else:
            # Navigation options for non-logged-in users
            selected = st.radio(
                "Navigation",
                ["Login", "Register"],
            )

            # Handle navigation
            if selected == "Login":
                login_page()
            elif selected == "Register":
                register_page()


def main():
    """
    Main application function.
    """
    # Initialize session state for page navigation
    if "page" not in st.session_state:
        st.session_state.page = "dashboard"

    # Render the sidebar
    sidebar()


if __name__ == "__main__":
    main()
