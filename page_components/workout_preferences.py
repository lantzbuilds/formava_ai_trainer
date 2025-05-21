"""
Workout preferences page for the AI Personal Trainer application.
"""

import logging
from datetime import datetime, timezone

import streamlit as st

from config.database import Database
from models.user import FitnessGoal, InjurySeverity, UserProfile
from utils.units import format_height_cm, format_weight_kg

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
db = Database()


def workout_preferences_page():
    """Display the workout preferences page."""
    st.title("Workout Preferences")

    # Get user document from database
    user_doc = db.get_document(st.session_state.user_id)
    if not user_doc:
        st.error("User profile not found")
        return

    # Fix type issues before creating UserProfile instance
    if "preferred_workout_days" in user_doc and isinstance(
        user_doc["preferred_workout_days"], list
    ):
        # Take the first value if it's a list
        user_doc["preferred_workout_days"] = user_doc["preferred_workout_days"][0]
        logger.info(
            f"Converted preferred_workout_days from list to integer: {user_doc['preferred_workout_days']}"
        )

    # Create UserProfile instance
    user = UserProfile(**user_doc)

    # Display current preferences
    st.subheader("Current Preferences")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Days per week:** {user_doc.get('preferred_workout_days', 3)}")
        st.write(
            f"**Workout duration:** {user_doc.get('preferred_workout_duration', 60)} minutes"
        )
        st.write(
            f"**Preferred time:** {user_doc.get('preferred_workout_time', 'Not specified')}"
        )
        st.write(
            f"**Experience level:** {user_doc.get('experience_level', 'Not specified')}"
        )
        st.write(f"**Fitness goals:** {', '.join(user_doc.get('fitness_goals', []))}")

    with col2:
        st.write(f"**Height:** {format_height_cm(user_doc.get('height_cm', 0))}")
        st.write(f"**Weight:** {format_weight_kg(user_doc.get('weight_kg', 0))}")
        st.write(f"**Age:** {user_doc.get('age', 'Not specified')}")
        st.write(f"**Sex:** {user_doc.get('sex', 'Not specified')}")

    # Edit preferences
    st.subheader("Edit Preferences")
    with st.form("edit_preferences"):
        # Workout Preferences
        preferred_workout_days = st.slider(
            "Days per week you plan to work out",
            min_value=1,
            max_value=7,
            value=user_doc.get("preferred_workout_days", 3),
            step=1,
        )
        preferred_workout_duration = st.slider(
            "Preferred workout duration (minutes)",
            min_value=15,
            max_value=180,
            value=user_doc.get("preferred_workout_duration", 60),
            step=15,
        )
        preferred_workout_time = st.selectbox(
            "Preferred workout time",
            ["morning", "afternoon", "evening", "anytime"],
            index=(
                ["morning", "afternoon", "evening", "anytime"].index(
                    user_doc.get("preferred_workout_time", "anytime")
                )
                if user_doc.get("preferred_workout_time")
                in ["morning", "afternoon", "evening", "anytime"]
                else 3
            ),
        )

        # Fitness Goals
        new_goals = st.multiselect(
            "Fitness Goals",
            [g.value for g in FitnessGoal],
            default=user_doc.get("fitness_goals", []),
        )

        # Experience Level
        experience = st.selectbox(
            "Experience Level",
            ["beginner", "intermediate", "advanced"],
            index=["beginner", "intermediate", "advanced"].index(
                user_doc.get("experience_level", "beginner")
            ),
        )

        if st.form_submit_button("Update Preferences"):
            try:
                # Update user profile
                user_doc["preferred_workout_days"] = preferred_workout_days
                user_doc["preferred_workout_duration"] = preferred_workout_duration
                user_doc["preferred_workout_time"] = preferred_workout_time
                user_doc["fitness_goals"] = new_goals
                user_doc["experience_level"] = experience
                user_doc["updated_at"] = datetime.now(timezone.utc).isoformat()

                # Save to database
                doc_id, doc_rev = db.save_document(user_doc)
                logger.info(f"Updated user preferences with ID: {doc_id}")

                st.success("Preferences updated successfully!")
                st.rerun()
            except Exception as e:
                logger.error(f"Error updating preferences: {str(e)}")
                st.error(f"Failed to update preferences: {str(e)}")

    # Injury Management
    st.subheader("Injury Management")

    # Initialize session state for injuries if not exists
    if "injuries" not in st.session_state:
        st.session_state.injuries = user_doc.get("injuries", [])

    # Display existing injuries
    if st.session_state.injuries:
        for i, injury in enumerate(st.session_state.injuries):
            with st.expander(
                f"Injury {i+1}: {injury.get('description', 'Unnamed')} - {injury.get('body_part', 'Unknown body part')}"
            ):
                st.write(f"**Description:** {injury.get('description', 'N/A')}")
                st.write(f"**Body Part:** {injury.get('body_part', 'N/A')}")
                st.write(f"**Severity:** {injury.get('severity', 'N/A')}")
                st.write(f"**Date Injured:** {injury.get('date_injured', 'N/A')}")
                st.write(
                    f"**Currently Active:** {'Yes' if injury.get('is_active', True) else 'No'}"
                )
                if injury.get("notes"):
                    st.write(f"**Notes:** {injury.get('notes', 'N/A')}")

                if st.button(f"Remove Injury {i+1}", key=f"remove_{i}"):
                    st.session_state.injuries.pop(i)
                    # Update the database
                    user_doc["injuries"] = st.session_state.injuries
                    user_doc["updated_at"] = datetime.now(timezone.utc).isoformat()
                    db.save_document(user_doc)
                    st.rerun()
    else:
        st.info("No injuries recorded.")

    # Add new injury
    st.subheader("Add New Injury")
    with st.form("injury_form"):
        description = st.text_input(
            "Description",
            help="Brief description of the injury (e.g., 'Torn ACL', 'Rotator cuff strain')",
        )
        body_part = st.text_input(
            "Body Part",
            help="The specific body part affected (e.g., 'Left knee', 'Right shoulder')",
        )
        severity = st.selectbox(
            "Severity",
            [s.value for s in InjurySeverity],
            help="How severe the injury is. Mild: minor discomfort, Moderate: affects daily activities, Severe: requires medical attention",
        )
        date_injured = st.date_input(
            "Date Injured",
            value=datetime.now().date(),
            help="When the injury occurred",
        )
        is_active = st.checkbox(
            "Currently Active",
            value=True,
            help="Check if you're still experiencing symptoms from this injury",
        )
        notes = st.text_area(
            "Notes",
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

                # Update the database
                user_doc["injuries"] = st.session_state.injuries
                user_doc["updated_at"] = datetime.now(timezone.utc).isoformat()
                db.save_document(user_doc)

                st.success("Injury added successfully!")
                st.rerun()
            else:
                st.error("Description and Body Part are required")
