"""
Profile page for the AI Personal Trainer application.
"""

import logging
from datetime import datetime, timezone

import gradio as gr

from app.config.database import Database
from app.models.user import FitnessGoal, InjurySeverity, Sex, UserProfile
from app.utils.crypto import encrypt_api_key
from app.utils.units import cm_to_inches, kg_to_lbs

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database connection
db = Database()


def profile_view(state):
    """Display the profile page."""
    with gr.Column():
        gr.Markdown("## Profile")

        # Personal Information Section
        with gr.Group():
            gr.Markdown("### Personal Information")
            with gr.Row():
                username = gr.Textbox(label="Username", interactive=False)
                email = gr.Textbox(label="Email", interactive=False)
            with gr.Row():
                age = gr.Number(label="Age", interactive=False)
                sex = gr.Dropdown(
                    label="Sex",
                    choices=[s.value for s in Sex],
                    interactive=False,
                )
            with gr.Row():
                height_feet = gr.Number(label="Height (feet)", interactive=False)
                height_inches = gr.Number(label="Height (inches)", interactive=False)
                weight_lbs = gr.Number(label="Weight (lbs)", interactive=False)

        # Fitness Information Section
        with gr.Group():
            gr.Markdown("### Fitness Information")
            with gr.Row():
                experience = gr.Dropdown(
                    label="Experience Level",
                    choices=["beginner", "intermediate", "advanced"],
                    interactive=False,
                )
                goals = gr.CheckboxGroup(
                    label="Fitness Goals",
                    choices=[g.value for g in FitnessGoal],
                    interactive=False,
                )
            with gr.Row():
                workout_days = gr.Number(
                    label="Preferred Workout Days per Week",
                    interactive=False,
                )
                workout_duration = gr.Number(
                    label="Preferred Workout Duration (minutes)",
                    interactive=False,
                )

        # Hevy API Integration Section
        with gr.Group():
            gr.Markdown("### Hevy API Integration")
            hevy_status = gr.Markdown("Checking Hevy API status...")
            with gr.Row():
                hevy_api_key = gr.Textbox(
                    label="Hevy API Key",
                    type="password",
                    placeholder="Enter your Hevy API key",
                )
                save_hevy_key = gr.Button("Save Hevy API Key")

        # Injuries Section
        with gr.Group():
            gr.Markdown("### Injuries")
            injuries_list = gr.Markdown("Loading injuries...")
            with gr.Group():
                gr.Markdown("#### Add New Injury")
                with gr.Row():
                    injury_desc = gr.Textbox(
                        label="Description",
                        placeholder="Brief description of the injury",
                    )
                    injury_part = gr.Textbox(
                        label="Body Part",
                        placeholder="The specific body part affected",
                    )
                with gr.Row():
                    injury_severity = gr.Dropdown(
                        label="Severity",
                        choices=[s.value for s in InjurySeverity],
                    )
                    injury_date = gr.DateTime(
                        label="Date Injured",
                        interactive=True,
                        include_time=False,
                    )
                with gr.Row():
                    injury_active = gr.Checkbox(label="Currently Active", value=True)
                    injury_notes = gr.Textbox(
                        label="Notes",
                        placeholder="Additional details about the injury",
                    )
                add_injury_btn = gr.Button("Add Injury")

        def load_profile(user_state):
            """Load user profile data."""
            if not user_state:
                return (
                    gr.update(value="Please log in to view your profile"),
                    gr.update(value=""),
                    gr.update(value=""),
                    gr.update(value=None),
                    gr.update(value=None),
                    gr.update(value=None),
                    gr.update(value=None),
                    gr.update(value=None),
                    gr.update(value=None),
                    gr.update(value=None),
                    gr.update(value=None),
                    gr.update(value=None),
                    gr.update(value="Please log in to view your profile"),
                    gr.update(value=""),
                )

            try:
                # Get user profile
                user_doc = db.get_document(user_state["id"])
                if not user_doc:
                    return (
                        gr.update(value="Error: User profile not found"),
                        gr.update(value=""),
                        gr.update(value=""),
                        gr.update(value=None),
                        gr.update(value=None),
                        gr.update(value=None),
                        gr.update(value=None),
                        gr.update(value=None),
                        gr.update(value=None),
                        gr.update(value=None),
                        gr.update(value=None),
                        gr.update(value=None),
                        gr.update(value="Error: User profile not found"),
                        gr.update(value=""),
                    )

                user = UserProfile.from_dict(user_doc)

                # Convert height from cm to feet and inches
                height_inches_total = cm_to_inches(user.height_cm)
                height_feet_val = int(height_inches_total // 12)
                height_inches_val = int(height_inches_total % 12)

                # Convert weight from kg to lbs
                weight_lbs_val = kg_to_lbs(user.weight_kg)

                # Format injuries list
                injuries_text = "No injuries recorded"
                if user.injuries:
                    injuries_text = "### Current Injuries\n"
                    for i, injury in enumerate(user.injuries, 1):
                        injuries_text += f"\n#### Injury {i}\n"
                        injuries_text += f"- **Description:** {injury.description}\n"
                        injuries_text += f"- **Body Part:** {injury.body_part}\n"
                        injuries_text += f"- **Severity:** {injury.severity.value}\n"
                        injuries_text += f"- **Date Injured:** {injury.date_injured.strftime('%Y-%m-%d')}\n"
                        injuries_text += f"- **Currently Active:** {'Yes' if injury.is_active else 'No'}\n"
                        if injury.notes:
                            injuries_text += f"- **Notes:** {injury.notes}\n"

                # Format Hevy API status
                hevy_status_text = "Hevy API key is not configured"
                if user.hevy_api_key:
                    hevy_status_text = "Hevy API key is configured"
                    if user.hevy_api_key_updated_at:
                        hevy_status_text += f" (Last updated: {user.hevy_api_key_updated_at.strftime('%Y-%m-%d')})"

                return (
                    gr.update(value=user.username),
                    gr.update(value=user.email),
                    gr.update(value=user.age),
                    gr.update(value=user.sex.value),
                    gr.update(value=height_feet_val),
                    gr.update(value=height_inches_val),
                    gr.update(value=weight_lbs_val),
                    gr.update(value=user.experience_level),
                    gr.update(value=[g.value for g in user.fitness_goals]),
                    gr.update(value=user.preferred_workout_days),
                    gr.update(value=user.preferred_workout_duration),
                    gr.update(value=hevy_status_text),
                    gr.update(value=injuries_text),
                    gr.update(value=""),
                )

            except Exception as e:
                logger.error(f"Error loading profile: {str(e)}", exc_info=True)
                return (
                    gr.update(value="Error loading profile"),
                    gr.update(value=""),
                    gr.update(value=""),
                    gr.update(value=None),
                    gr.update(value=None),
                    gr.update(value=None),
                    gr.update(value=None),
                    gr.update(value=None),
                    gr.update(value=None),
                    gr.update(value=None),
                    gr.update(value=None),
                    gr.update(value="Error loading profile"),
                    gr.update(value=""),
                    gr.update(value=str(e)),
                )

        def save_profile(user_state, hevy_api_key):
            """Save profile changes."""
            if not user_state:
                return gr.update(value="Please log in to save changes")

            try:
                # Get current user document
                user_doc = db.get_document(user_state["id"])
                if not user_doc:
                    return gr.update(value="Error: User profile not found")

                user = UserProfile.from_dict(user_doc)

                # Update Hevy API key if provided
                if hevy_api_key:
                    encrypted_key = encrypt_api_key(hevy_api_key)
                    user.hevy_api_key = encrypted_key
                    user.hevy_api_key_updated_at = datetime.now(timezone.utc)

                    # Save changes
                    update_doc = user.model_dump()
                    update_doc["_rev"] = user_doc["_rev"]
                    db.save_document(update_doc, doc_id=user_state["id"])

                    # Return success message with timestamp
                    timestamp = user.hevy_api_key_updated_at.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    return gr.update(
                        value=f"Hevy API key saved successfully at {timestamp}"
                    )
                else:
                    return gr.update(value="No API key provided")

            except Exception as e:
                logger.error(f"Error saving profile: {str(e)}", exc_info=True)
                return gr.update(value=f"Error saving profile: {str(e)}")

        def add_injury(
            user_state, description, body_part, severity, date_injured, is_active, notes
        ):
            """Add a new injury to the user's profile."""
            if not user_state:
                return gr.update(value="Please log in to add injuries")

            if not description or not body_part:
                return gr.update(value="Description and Body Part are required")

            try:
                # Get current user document
                user_doc = db.get_document(user_state["id"])
                if not user_doc:
                    return gr.update(value="Error: User profile not found")

                user = UserProfile.from_dict(user_doc)

                # Create new injury
                new_injury = {
                    "description": description,
                    "body_part": body_part,
                    "severity": severity,
                    "date_injured": date_injured,
                    "is_active": is_active,
                    "notes": notes,
                }

                # Add injury to user's profile
                user.injuries.append(new_injury)

                # Save changes
                update_doc = user.model_dump()
                update_doc["_rev"] = user_doc["_rev"]
                db.save_document(update_doc, doc_id=user_state["id"])

                return gr.update(value="Injury added successfully")

            except Exception as e:
                logger.error(f"Error adding injury: {str(e)}", exc_info=True)
                return gr.update(value=f"Error adding injury: {str(e)}")

        # Setup event handlers
        save_hevy_key.click(
            fn=save_profile,
            inputs=[state["user_state"], hevy_api_key],
            outputs=[hevy_status],
        ).then(
            fn=load_profile,
            inputs=[state["user_state"]],
            outputs=[
                username,
                email,
                age,
                sex,
                height_feet,
                height_inches,
                weight_lbs,
                experience,
                goals,
                workout_days,
                workout_duration,
                hevy_status,
                injuries_list,
                gr.Textbox(visible=False),
            ],
        )

        add_injury_btn.click(
            fn=add_injury,
            inputs=[
                gr.State(),
                injury_desc,
                injury_part,
                injury_severity,
                injury_date,
                injury_active,
                injury_notes,
            ],
            outputs=[injuries_list],
        )

        return (
            username,
            email,
            age,
            sex,
            height_feet,
            height_inches,
            weight_lbs,
            experience,
            goals,
            workout_days,
            workout_duration,
            hevy_status,
            injuries_list,
            gr.Textbox(visible=False),
            load_profile,
        )
