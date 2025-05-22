"""
Registration page for the AI Personal Trainer application.
"""

import logging
from datetime import datetime, timezone

import streamlit as st

from config.config import HEVY_API_KEY
from config.database import Database
from models.user import FitnessGoal, InjurySeverity, Sex, UserProfile
from utils.crypto import encrypt_api_key
from utils.units import inches_to_cm, lbs_to_kg

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database connection
db = Database()


def register_page():
    """Display the registration page."""
    st.title("Register")

    # Initialize session state for injuries if not exists
    if "injuries" not in st.session_state:
        st.session_state.injuries = []

    # Main registration form
    with st.form("register_form"):
        username = st.text_input("Username")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")

        col1, col2 = st.columns(2)
        with col1:
            # Height in feet and inches
            height_feet = st.number_input(
                "Height (feet)", min_value=3, max_value=8, value=5
            )
            height_inches = st.number_input(
                "Height (inches)", min_value=0, max_value=11, value=10
            )
            # Convert to cm for storage
            height_cm = inches_to_cm(height_feet * 12 + height_inches)

            # Weight in pounds
            weight_lbs = st.number_input(
                "Weight (lbs)", min_value=50, max_value=500, value=150
            )
            # Convert to kg for storage
            weight_kg = lbs_to_kg(weight_lbs)

            sex = st.selectbox("Sex", [s.value for s in Sex])

        with col2:
            age = st.number_input("Age", min_value=13, max_value=120, value=30)
            experience = st.selectbox(
                "Experience Level", ["beginner", "intermediate", "advanced"]
            )
            goals = st.multiselect("Fitness Goals", [g.value for g in FitnessGoal])

            # Workout Preferences
            preferred_workout_days = st.slider(
                "Days per week you plan to work out",
                min_value=1,
                max_value=7,
                value=3,
                step=1,
            )
            preferred_workout_duration = st.slider(
                "Preferred workout duration (minutes)",
                min_value=15,
                max_value=180,
                value=60,
                step=15,
            )

        # Hevy API Integration
        st.subheader("Hevy API Integration (Optional)")
        hevy_api_key = st.text_input(
            "Hevy API Key",
            type="password",
            help="You can add this later in your profile",
        )

        # Handle API key encryption
        encrypted_key = None
        if hevy_api_key and hevy_api_key.strip():
            try:
                encrypted_key = encrypt_api_key(hevy_api_key)
            except Exception as e:
                st.error(f"Error encrypting Hevy API key: {str(e)}")
                return
        elif HEVY_API_KEY:  # Use demo key if no user key provided
            try:
                encrypted_key = encrypt_api_key(HEVY_API_KEY)
                st.info(
                    "Using demo Hevy API key. You can update this later in your profile."
                )
            except Exception as e:
                logger.error(f"Error encrypting demo Hevy API key: {str(e)}")

        submit = st.form_submit_button("Register")

    # Separate form for injuries
    st.subheader("Injuries (Optional)")
    injury_count = st.number_input(
        "Number of injuries to add",
        min_value=0,
        max_value=5,
        value=len(st.session_state.injuries),
        key="injury_count",
    )

    # Display existing injuries
    for i, injury in enumerate(st.session_state.injuries):
        with st.expander(f"Injury {i+1}"):
            st.write(f"**Description:** {injury['description']}")
            st.write(f"**Body Part:** {injury['body_part']}")
            st.write(f"**Severity:** {injury['severity']}")
            st.write(f"**Date Injured:** {injury['date_injured']}")
            st.write(f"**Currently Active:** {'Yes' if injury['is_active'] else 'No'}")
            if injury["notes"]:
                st.write(f"**Notes:** {injury['notes']}")
            if st.button(f"Remove Injury {i+1}", key=f"remove_{i}"):
                st.session_state.injuries.pop(i)
                st.rerun()

    # Add new injuries
    if injury_count > len(st.session_state.injuries):
        with st.form("injury_form"):
            st.write("### Add New Injury")
            description = st.text_input(
                "Description",
                key="new_injury_desc",
                help="Brief description of the injury (e.g., 'Torn ACL', 'Rotator cuff strain')",
            )
            body_part = st.text_input(
                "Body Part",
                key="new_injury_part",
                help="The specific body part affected (e.g., 'Left knee', 'Right shoulder')",
            )
            severity = st.selectbox(
                "Severity",
                [s.value for s in InjurySeverity],
                key="new_injury_severity",
                help="How severe the injury is. Mild: minor discomfort, Moderate: affects daily activities, Severe: requires medical attention",
            )
            date_injured = st.date_input(
                "Date Injured",
                value=datetime.now().date(),
                key="new_injury_date",
                help="When the injury occurred",
            )
            is_active = st.checkbox(
                "Currently Active",
                value=True,
                key="new_injury_active",
                help="Check if you're still experiencing symptoms from this injury",
            )
            notes = st.text_area(
                "Notes",
                key="new_injury_notes",
                help="Additional details about the injury, treatment, or recovery process",
            )

            if st.form_submit_button("Add Injury"):
                if description and body_part:
                    new_injury = {
                        "description": description,
                        "body_part": body_part,
                        "severity": severity,
                        "date_injured": datetime.combine(
                            date_injured, datetime.min.time()
                        ).isoformat(),
                        "is_active": is_active,
                        "notes": notes,
                    }
                    st.session_state.injuries.append(new_injury)
                    st.rerun()
                else:
                    st.error("Description and Body Part are required")

    # Handle registration submission
    if submit:
        if password != confirm_password:
            st.error("Passwords do not match")
        else:
            try:
                # Check if username already exists
                if db.username_exists(username):
                    st.error(
                        "Username already exists. Please choose a different username."
                    )
                    return

                logger.info(f"Creating new user: {username}")
                # Create new user
                new_user = UserProfile.create_user(
                    username=username,
                    email=email,
                    password=password,
                    height_cm=height_cm,
                    weight_kg=weight_kg,
                    sex=Sex(sex),
                    age=age,
                    fitness_goals=[FitnessGoal(g) for g in goals],
                    experience_level=experience,
                    preferred_workout_days=preferred_workout_days,
                    preferred_workout_duration=preferred_workout_duration,
                    hevy_api_key=encrypted_key,  # Will be None if no keys available
                    injuries=st.session_state.injuries,
                )

                logger.info(f"User object created successfully. Type: {new_user.type}")
                logger.debug(f"User object: {new_user.model_dump()}")

                # Save to database
                logger.info("Saving user to database...")
                user_dict = new_user.model_dump()
                doc_id, doc_rev = db.save_document(user_dict)
                logger.info(f"User saved successfully. ID: {doc_id}, Rev: {doc_rev}")

                st.success(f"Registration successful! Welcome, {username}!")
                st.session_state.user_id = doc_id
                st.session_state.username = username
                st.session_state.injuries = []
                st.rerun()
            except Exception as e:
                logger.error(f"Registration failed: {str(e)}", exc_info=True)
                st.error(f"Registration failed: {str(e)}")
                st.write(f"Debug: Error details: {type(e).__name__}")
