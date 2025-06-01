"""
Profile page for the AI Personal Trainer application.
"""

import logging
from datetime import datetime, timezone

import streamlit as st

from config.database import Database
from models.user import FitnessGoal, InjurySeverity, Sex, UserProfile
from utils.crypto import decrypt_api_key, encrypt_api_key
from utils.units import cm_to_inches, kg_to_lbs

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database connection
db = Database()


def profile_page():
    """Display the profile page."""
    st.title("Profile")

    # Get user document from database
    user_doc = db.get_document(st.session_state.user_id)
    if not user_doc:
        st.error("User profile not found")
        return

    # Create UserProfile instance
    user = UserProfile(**user_doc)

    # Display user information
    st.subheader("Personal Information")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Username:** {user.username}")
        st.write(f"**Email:** {user.email}")
        st.write(f"**Age:** {user.age}")
        st.write(f"**Sex:** {user.sex.value}")
        # Convert height from cm to feet and inches
        height_inches = cm_to_inches(user.height_cm)
        height_feet = int(height_inches // 12)
        height_inches = int(height_inches % 12)
        st.write(f"**Height:** {height_feet}'{height_inches}\"")
        # Convert weight from kg to lbs
        weight_lbs = kg_to_lbs(user.weight_kg)
        st.write(f"**Weight:** {weight_lbs:.1f} lbs")

    with col2:
        st.write(f"**Experience Level:** {user.experience_level}")
        st.write(
            f"**Fitness Goals:** {', '.join([g.value for g in user.fitness_goals])}"
        )
        st.write(
            f"**Preferred Workout Days:** {user.preferred_workout_days} days per week"
        )
        st.write(
            f"**Preferred Workout Duration:** {user.preferred_workout_duration} minutes"
        )

    # Display Hevy API key status
    st.subheader("Hevy API Integration")
    if user.hevy_api_key:
        st.success("Hevy API key is configured")
        if st.button("Remove Hevy API Key"):
            try:
                # Get the current document to preserve _rev
                current_doc = db.get_document(st.session_state.user_id)
                if not current_doc:
                    raise Exception("User document not found")

                # Update user document to remove API key
                user.hevy_api_key = None
                user.hevy_api_key_updated_at = None

                # Create update document with _rev
                update_doc = user.model_dump()
                update_doc["_rev"] = current_doc["_rev"]

                # Save the updated document
                db.save_document(update_doc, doc_id=st.session_state.user_id)
                st.success("Hevy API key removed successfully")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to remove Hevy API key: {str(e)}")
    else:
        st.warning("Hevy API key is not configured")
        with st.form("hevy_api_form"):
            hevy_api_key = st.text_input(
                "Hevy API Key",
                type="password",
                help="Enter your Hevy API key to enable workout tracking",
            )
            if st.form_submit_button("Save Hevy API Key"):
                if hevy_api_key:
                    try:
                        # Get the current document to preserve _rev
                        current_doc = db.get_document(st.session_state.user_id)
                        if not current_doc:
                            raise Exception("User document not found")

                        # Encrypt and save API key
                        encrypted_key = encrypt_api_key(hevy_api_key)
                        user.hevy_api_key = encrypted_key
                        user.hevy_api_key_updated_at = datetime.now(timezone.utc)

                        # Create update document with _rev
                        update_doc = user.model_dump()
                        update_doc["_rev"] = current_doc["_rev"]

                        # Save the updated document
                        db.save_document(update_doc, doc_id=st.session_state.user_id)
                        st.success("Hevy API key saved successfully")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to save Hevy API key: {str(e)}")
                else:
                    st.error("Please enter a Hevy API key")

    # Display injuries
    st.subheader("Injuries")
    if user.injuries:
        for i, injury in enumerate(user.injuries):
            with st.expander(f"Injury {i+1}"):
                st.write(f"**Description:** {injury.description}")
                st.write(f"**Body Part:** {injury.body_part}")
                st.write(f"**Severity:** {injury.severity.value}")
                st.write(
                    f"**Date Injured:** {injury.date_injured.strftime('%Y-%m-%d')}"
                )
                st.write(f"**Currently Active:** {'Yes' if injury.is_active else 'No'}")
                if injury.notes:
                    st.write(f"**Notes:** {injury.notes}")
    else:
        st.info("No injuries recorded")

    # Add new injury
    st.subheader("Add New Injury")
    with st.form("new_injury_form"):
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
                user.injuries.append(new_injury)
                db.save_document(user.model_dump(), doc_id=st.session_state.user_id)
                st.success("Injury added successfully")
                st.rerun()
            else:
                st.error("Description and Body Part are required")
