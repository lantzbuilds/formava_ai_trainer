"""
Profile page for the AI Personal Trainer application.
"""

import logging
import sys
from datetime import datetime, timedelta, timezone

import gradio as gr
import requests

from app.config.database import Database
from app.models.user import FitnessGoal, Injury, InjurySeverity, Sex, UserProfile
from app.services.hevy_api import HevyAPI
from app.utils.crypto import encrypt_api_key
from app.utils.units import cm_to_inches, kg_to_lbs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add a test log message
logger.info("Profile module loaded")

# Initialize database connection
db = Database()


def profile_view(state):
    """Display the profile page."""
    logger.info("Initializing profile view with state")
    logger.info(f"User state in profile view: {state}")
    logger.info(f"User state type: {type(state)}")
    logger.info(
        f"User state value: {state.value if hasattr(state, 'value') else state}"
    )

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

            # Add sync controls
            with gr.Row():
                sync_recent_btn = gr.Button(
                    "Sync Recent Workouts (Last 30 Days)", interactive=False
                )
                sync_full_btn = gr.Button("Sync Full History", interactive=False)
            sync_status = gr.Markdown("")

        # Injuries Section
        with gr.Group() as injuries_container:
            gr.Markdown("### Injuries")
            injuries_list = gr.Markdown("Loading injuries...")
            # Add New Injury Form
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
                add_injury_btn = gr.Button("Add Injury", variant="primary")

        # Injury Controls Section (outside injuries_container)
        with gr.Group():
            gr.Markdown("#### Injury Controls")
            with gr.Row():
                with gr.Column(scale=1):
                    injury_index = gr.Number(
                        label="Injury Number", interactive=True, minimum=1, step=1
                    )
                with gr.Column(scale=2):
                    with gr.Row():
                        toggle_active_btn = gr.Button(
                            "Toggle Active Status", variant="secondary"
                        )
                        delete_injury_btn = gr.Button("Delete Injury", variant="stop")

        def load_profile(user_state):
            """Load user profile data."""
            logger.info("Loading profile with user state")
            logger.info(f"User state type: {type(user_state)}")
            logger.info(f"User state value: {user_state}")
            logger.info(
                f"User state value type: {type(user_state.value) if hasattr(user_state, 'value') else 'No value attribute'}"
            )

            if not user_state:
                logger.warning("No user state provided")
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
                )

            try:
                # Get user profile
                user_id = (
                    user_state.value.get("id")
                    if hasattr(user_state, "value")
                    else user_state.get("id")
                )
                logger.info(f"Loading profile for user ID: {user_id}")

                user_doc = db.get_document(user_id)
                if not user_doc:
                    logger.error(f"User document not found for ID: {user_id}")
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
                    )

                user = UserProfile.from_dict(user_doc)
                logger.info(f"Loaded profile for user: {user.username}")

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
                        date_injured = injury.date_injured
                        if hasattr(date_injured, "strftime"):
                            date_str = date_injured.strftime("%Y-%m-%d")
                        else:
                            date_str = str(date_injured)
                        injuries_text += f"- **Date Injured:** {date_str}\n"
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
                )

        def save_profile(user_state, hevy_api_key):
            """Save profile changes."""
            logger.info("Saving profile with user state")
            logger.info(f"User state type: {type(user_state)}")
            logger.info(f"User state value: {user_state}")
            logger.info(
                f"User state value type: {type(user_state.value) if hasattr(user_state, 'value') else 'No value attribute'}"
            )

            if not user_state:
                return gr.update(value="Please log in to save changes")

            try:
                # Get current user document
                user_id = (
                    user_state.value.get("id")
                    if hasattr(user_state, "value")
                    else user_state.get("id")
                )
                logger.info(f"Saving profile for user ID: {user_id}")

                user_doc = db.get_document(user_id)
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
                    db.save_document(update_doc, doc_id=user_id)

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
            logger.info(f"Adding injury with user state: {user_state}")
            if not user_state:
                logger.warning("No user state provided when adding injury")
                return gr.update(value="Please log in to add injuries")

            if not description or not body_part:
                logger.warning("Missing required fields: description or body part")
                return gr.update(value="Description and Body Part are required")

            try:
                # Get current user document
                user_id = (
                    user_state.value["id"]
                    if hasattr(user_state, "value")
                    else user_state["id"]
                )
                user_doc = db.get_document(user_id)
                if not user_doc:
                    logger.error(f"User document not found for ID: {user_state['id']}")
                    return gr.update(value="Error: User profile not found")

                user = UserProfile.from_dict(user_doc)
                logger.info(f"Found user profile for: {user.username}")

                # Create new injury
                new_injury = Injury(
                    description=description,
                    body_part=body_part,
                    severity=severity,
                    date_injured=date_injured,
                    is_active=is_active,
                    notes=notes,
                )
                logger.info(f"Created new injury: {new_injury}")

                # Add injury to user's profile
                if not isinstance(user.injuries, list):
                    user.injuries = []
                user.injuries.append(new_injury)

                # Save changes
                update_doc = user.model_dump()
                update_doc["_rev"] = user_doc["_rev"]
                db.save_document(update_doc, doc_id=user_id)
                logger.info("Successfully saved injury to user profile")

                return gr.update(value="Injury added successfully")

            except Exception as e:
                logger.error(f"Error adding injury: {str(e)}", exc_info=True)
                return gr.update(value=f"Error adding injury: {str(e)}")

        def toggle_injury_active(user_state, injury_index):
            """Toggle the active status of an injury."""
            logger.info(f"Toggling injury {injury_index} active status")
            if not user_state:
                return gr.update(value="Please log in to modify injuries")

            try:
                # Get current user document
                user_id = (
                    user_state.value["id"]
                    if hasattr(user_state, "value")
                    else user_state["id"]
                )
                user_doc = db.get_document(user_id)
                if not user_doc:
                    return gr.update(value="Error: User profile not found")

                user = UserProfile.from_dict(user_doc)

                # Convert index to 0-based and validate
                idx = int(injury_index) - 1
                if idx < 0 or idx >= len(user.injuries):
                    return gr.update(value="Invalid injury index")

                # Toggle active status
                user.injuries[idx].is_active = not user.injuries[idx].is_active

                # Save changes
                update_doc = user.model_dump()
                update_doc["_rev"] = user_doc["_rev"]
                db.save_document(update_doc, doc_id=user_id)
                logger.info(f"Successfully toggled injury {injury_index} active status")

                return gr.update(value="Injury status updated successfully")

            except Exception as e:
                logger.error(f"Error toggling injury status: {str(e)}", exc_info=True)
                return gr.update(value=f"Error updating injury status: {str(e)}")

        def delete_injury(user_state, injury_index):
            """Delete an injury from the user's profile."""
            logger.info(f"Deleting injury {injury_index}")
            if not user_state:
                return gr.update(value="Please log in to delete injuries")

            try:
                # Get current user document
                user_id = (
                    user_state.value["id"]
                    if hasattr(user_state, "value")
                    else user_state["id"]
                )
                user_doc = db.get_document(user_id)
                if not user_doc:
                    return gr.update(value="Error: User profile not found")

                user = UserProfile.from_dict(user_doc)

                # Convert index to 0-based and validate
                idx = int(injury_index) - 1
                if idx < 0 or idx >= len(user.injuries):
                    return gr.update(value="Invalid injury index")

                # Remove injury
                del user.injuries[idx]

                # Save changes
                update_doc = user.model_dump()
                update_doc["_rev"] = user_doc["_rev"]
                db.save_document(update_doc, doc_id=user_id)
                logger.info(f"Successfully deleted injury {injury_index}")

                return gr.update(value="Injury deleted successfully")

            except Exception as e:
                logger.error(f"Error deleting injury: {str(e)}", exc_info=True)
                return gr.update(value=f"Error deleting injury: {str(e)}")

        def sync_workouts(user_state, sync_type="recent"):
            """Sync workouts from Hevy API."""
            if not user_state:
                return gr.update(value="Please log in to sync workouts")

            try:
                # Get user profile
                user_id = (
                    user_state.value.get("id")
                    if hasattr(user_state, "value")
                    else user_state.get("id")
                )
                logger.info(f"Syncing workouts for user ID: {user_id}")

                user_doc = db.get_document(user_id)
                if not user_doc:
                    return gr.update(value="Error: User profile not found")

                user = UserProfile.from_dict(user_doc)
                if not user.hevy_api_key:
                    return gr.update(value="Please add your Hevy API key first")

                # Log API key status (without exposing the actual key)
                logger.info(
                    f"User {user.username} has API key: {bool(user.hevy_api_key)}"
                )
                logger.info(
                    f"API key length: {len(user.hevy_api_key) if user.hevy_api_key else 0}"
                )
                logger.info(f"API key last updated: {user.hevy_api_key_updated_at}")

                # Initialize Hevy API
                try:
                    logger.info("Initializing Hevy API client with encrypted key")
                    hevy_api = HevyAPI(api_key=user.hevy_api_key, is_encrypted=True)
                    logger.info("Successfully initialized Hevy API client")

                    # Test the API key with a simple request
                    logger.info("Testing API key with a simple request")
                    # Use a small date range for testing
                    test_end_date = datetime.now(timezone.utc)
                    test_start_date = test_end_date - timedelta(days=1)
                    test_workouts = hevy_api.get_workouts(
                        start_date=test_start_date, end_date=test_end_date
                    )
                    logger.info(
                        f"Test request successful, found {len(test_workouts) if test_workouts else 0} workouts"
                    )

                except Exception as e:
                    logger.error(f"Error initializing Hevy API client: {str(e)}")
                    if hasattr(e, "response"):
                        logger.error(f"Response status: {e.response.status_code}")
                        logger.error(f"Response headers: {e.response.headers}")
                        logger.error(f"Response body: {e.response.text}")
                    return gr.update(value=f"Error initializing Hevy API: {str(e)}")

                # Set date range based on sync type
                end_date = datetime.now(timezone.utc)
                if sync_type == "recent":
                    start_date = end_date - timedelta(days=30)
                    status_msg = "Syncing recent workouts (last 30 days)..."
                else:  # full sync
                    # Use a reasonable start date (e.g., 5 years ago)
                    start_date = end_date - timedelta(days=365 * 5)
                    status_msg = (
                        "Syncing full workout history (this may take a while)..."
                    )

                logger.info(f"Starting {sync_type} sync for user {user.username}")
                logger.info(f"Date range: {start_date} to {end_date}")

                # Get workouts
                try:
                    all_workouts = hevy_api.get_workouts(
                        start_date=start_date, end_date=end_date
                    )
                    logger.info(
                        f"API call completed. Response type: {type(all_workouts)}"
                    )
                except Exception as e:
                    logger.error(f"Error during API call: {str(e)}")
                    if hasattr(e, "response"):
                        logger.error(f"Response status: {e.response.status_code}")
                        logger.error(f"Response body: {e.response.text}")
                    return gr.update(value=f"Error fetching workouts: {str(e)}")

                if all_workouts:
                    logger.info(f"Found {len(all_workouts)} workouts to sync")
                    db.save_user_workouts(user_id, all_workouts)
                    logger.info(f"Successfully synced {len(all_workouts)} workouts")
                    return gr.update(
                        value=f"Successfully synced {len(all_workouts)} workouts"
                    )
                else:
                    logger.info("No workouts found to sync")
                    return gr.update(value="No workouts found to sync")

            except Exception as e:
                logger.error(f"Error syncing workouts: {str(e)}", exc_info=True)
                return gr.update(value=f"Error syncing workouts: {str(e)}")

        def update_hevy_status(user_state):
            """Update Hevy API status and button states."""
            logger.info("Updating Hevy status with user state")
            logger.info(f"User state type: {type(user_state)}")
            logger.info(f"User state value: {user_state}")
            logger.info(
                f"User state value type: {type(user_state.value) if hasattr(user_state, 'value') else 'No value attribute'}"
            )

            if not user_state:
                return (
                    gr.update(value="Please log in to view Hevy API status"),
                    gr.update(interactive=False),
                    gr.update(interactive=False),
                )

            try:
                # Get user profile
                user_id = (
                    user_state.value.get("id")
                    if hasattr(user_state, "value")
                    else user_state.get("id")
                )
                logger.info(f"Updating Hevy status for user ID: {user_id}")

                user_doc = db.get_document(user_id)
                if not user_doc:
                    return (
                        gr.update(value="Error: User profile not found"),
                        gr.update(interactive=False),
                        gr.update(interactive=False),
                    )

                user = UserProfile.from_dict(user_doc)
                has_api_key = bool(user.hevy_api_key)

                if has_api_key:
                    status_text = "Hevy API key is configured"
                    if user.hevy_api_key_updated_at:
                        status_text += f" (Last updated: {user.hevy_api_key_updated_at.strftime('%Y-%m-%d')})"
                    return (
                        gr.update(value=status_text),
                        gr.update(interactive=True),
                        gr.update(interactive=True),
                    )
                else:
                    return (
                        gr.update(value="Hevy API key is not configured"),
                        gr.update(interactive=False),
                        gr.update(interactive=False),
                    )

            except Exception as e:
                logger.error(f"Error updating Hevy status: {str(e)}", exc_info=True)
                return (
                    gr.update(value=f"Error checking Hevy API status: {str(e)}"),
                    gr.update(interactive=False),
                    gr.update(interactive=False),
                )

        # Setup event handlers
        logger.info("Setting up profile event handlers")

        def handle_add_injury(*args):
            """Wrapper function to handle add injury with logging."""
            logger.info("Add injury handler called")
            logger.info(f"Arguments received: {args}")
            try:
                result = add_injury(*args)
                logger.info(f"Add injury result: {result}")
                return result
            except Exception as e:
                logger.error(f"Error in handle_add_injury: {str(e)}", exc_info=True)
                raise

        # Update Hevy status and button states when profile loads
        def on_profile_load(user_state):
            """Handle profile load and update Hevy status."""
            logger.info("Profile load handler called")
            logger.info(f"User state type: {type(user_state)}")
            logger.info(f"User state value: {user_state}")
            logger.info(
                f"User state value type: {type(user_state.value) if hasattr(user_state, 'value') else 'No value attribute'}"
            )

            profile_updates = load_profile(user_state)
            hevy_updates = update_hevy_status(user_state)
            return (*profile_updates, *hevy_updates)

        # Connect profile load event
        gr.on(
            fn=on_profile_load,
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
                hevy_status,  # Duplicate for Hevy status update
                sync_recent_btn,
                sync_full_btn,
            ],
        )

        # Update Hevy status and button states after saving API key
        save_hevy_key.click(
            fn=save_profile,
            inputs=[state["user_state"], hevy_api_key],
            outputs=[hevy_status],
        ).then(
            fn=on_profile_load,
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
                hevy_status,  # Duplicate for Hevy status update
                sync_recent_btn,
                sync_full_btn,
            ],
        )

        logger.info("Setting up add injury button click handler")
        add_injury_btn.click(
            fn=handle_add_injury,
            inputs=[
                state["user_state"],
                injury_desc,
                injury_part,
                injury_severity,
                injury_date,
                injury_active,
                injury_notes,
            ],
            outputs=[injuries_list],
        ).then(
            fn=lambda x: load_profile(x),
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
            ],
        )

        # Connect injury action buttons
        toggle_active_btn.click(
            fn=toggle_injury_active,
            inputs=[state["user_state"], injury_index],
            outputs=[injuries_list],
        ).then(
            fn=lambda x: load_profile(x),
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
            ],
        )

        delete_injury_btn.click(
            fn=delete_injury,
            inputs=[state["user_state"], injury_index],
            outputs=[injuries_list],
        ).then(
            fn=lambda x: load_profile(x),
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
            ],
        )

        # Connect sync buttons
        sync_recent_btn.click(
            fn=lambda x: sync_workouts(x, "recent"),
            inputs=[state["user_state"]],
            outputs=[sync_status],
        )

        sync_full_btn.click(
            fn=lambda x: sync_workouts(x, "full"),
            inputs=[state["user_state"]],
            outputs=[sync_status],
        )

        logger.info("Profile view setup complete")

        return {
            "username": username,
            "email": email,
            "age": age,
            "sex": sex,
            "height_feet": height_feet,
            "height_inches": height_inches,
            "weight_lbs": weight_lbs,
            "experience": experience,
            "goals": goals,
            "workout_days": workout_days,
            "workout_duration": workout_duration,
            "hevy_status": hevy_status,
            "injuries_list": injuries_list,
            "injury_index": injury_index,
            "toggle_active_btn": toggle_active_btn,
            "delete_injury_btn": delete_injury_btn,
            "load_profile": load_profile,
        }
