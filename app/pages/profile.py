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

logger = logging.getLogger(__name__)

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
                weight_lbs = gr.Number(label="Weight (lbs)", interactive=True)

        # Fitness Information Section
        with gr.Group():
            gr.Markdown("### Fitness Information")
            with gr.Row():
                experience = gr.Dropdown(
                    label="Experience Level",
                    choices=["beginner", "intermediate", "advanced"],
                    interactive=True,
                )
                goals = gr.CheckboxGroup(
                    label="Fitness Goals",
                    choices=[g.value for g in FitnessGoal],
                    interactive=True,
                )
            with gr.Row():
                workout_days = gr.Number(
                    label="Preferred Workout Days per Week",
                    interactive=True,
                )
                workout_duration = gr.Number(
                    label="Preferred Workout Duration (minutes)",
                    interactive=True,
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

        # Add a hidden button for initial data loading
        load_data_btn = gr.Button("Load Data", visible=False)

        def update_profile(user_state):
            """Load user profile data."""
            logger.info("Loading profile with user state")
            logger.info(f"User state type: {type(user_state)}")
            logger.info(f"User state value: {user_state}")
            logger.info(
                f"User state value type: {type(user_state) if hasattr(user_state, 'value') else 'No value attribute'}"
            )

            if "id" not in user_state:
                logger.warning("No user id in user state provided")
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
                user_id = user_state.get("id")
                logger.info(f"Loading profile for user ID: {user_id}")
                if not user_id:
                    logger.error(
                        f"User ID not found in user state: {user_state}; cannot load profile"
                    )
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

        def save_profile(
            user_state,
            hevy_api_key=None,
            weight_lbs=None,
            experience_level=None,
            fitness_goals=None,
            preferred_workout_days=None,
            preferred_workout_duration=None,
        ):
            """Save profile changes: Hevy API key, weight, experience level, fitness goals, workout days, or duration."""
            logger.info("Saving profile with user state")
            logger.info(f"User state type: {type(user_state)}")
            logger.info(f"User state value: {user_state}")
            logger.info(
                f"User state value type: {type(user_state) if hasattr(user_state, 'value') else 'No value attribute'}"
            )

            msg = []
            if "id" not in user_state:
                msg.append("Please log in to save changes")
                return None
            try:
                # Get current user document
                user_id = user_state.get("id")
                logger.info(f"Saving profile for user ID: {user_id}")

                if not user_id:
                    logger.error(
                        f"User ID not found in user state: {user_state}; cannot save profile"
                    )
                    return None

                user_doc = db.get_document(user_id)
                if not user_doc:
                    msg.append("Error: User profile not found")
                    return None

                user = UserProfile.from_dict(user_doc)
                updated = False

                # Update Hevy API key if provided
                if hevy_api_key:
                    encrypted_key = encrypt_api_key(hevy_api_key)
                    user.hevy_api_key = encrypted_key
                    user.hevy_api_key_updated_at = datetime.now(timezone.utc)
                    updated = True
                    timestamp = user.hevy_api_key_updated_at.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    msg.append(f"Hevy API key saved successfully at {timestamp}")

                # Update weight if provided
                if weight_lbs is not None:
                    try:
                        weight_lbs_val = float(weight_lbs)
                    except Exception:
                        return gr.update(value="Invalid weight value")
                    # Only update if changed
                    current_weight_lbs = kg_to_lbs(user.weight_kg)
                    if abs(weight_lbs_val - current_weight_lbs) > 0.01:
                        from app.utils.units import lbs_to_kg

                        user.weight_kg = lbs_to_kg(weight_lbs_val)
                        # Append to weight_history
                        if not isinstance(user.weight_history, list):
                            user.weight_history = []
                        user.weight_history.append(
                            {
                                "weight": weight_lbs_val,
                                "date": datetime.now(timezone.utc),
                            }
                        )
                        updated = True
                        msg.append(f"Weight updated to {weight_lbs_val} lbs")
                    else:
                        msg.append("Weight unchanged")

                # Update experience level if provided
                if experience_level is not None:
                    if user.experience_level != experience_level:
                        user.experience_level = experience_level
                        updated = True
                        msg.append(f"Experience level updated to {experience_level}")

                # Update fitness goals if provided
                if fitness_goals is not None:
                    # Convert to FitnessGoal enums if needed
                    from app.models.user import FitnessGoal

                    new_goals = [
                        FitnessGoal(g) if not isinstance(g, FitnessGoal) else g
                        for g in fitness_goals
                    ]
                    if set(user.fitness_goals) != set(new_goals):
                        user.fitness_goals = new_goals
                        updated = True
                        msg.append(f"Fitness goals updated")

                # Update preferred workout days if provided
                if preferred_workout_days is not None:
                    try:
                        days_val = int(preferred_workout_days)
                    except Exception:
                        return gr.update(value="Invalid workout days value")
                    if user.preferred_workout_days != days_val:
                        user.preferred_workout_days = days_val
                        updated = True
                        msg.append(f"Preferred workout days updated to {days_val}")

                # Update preferred workout duration if provided
                if preferred_workout_duration is not None:
                    try:
                        duration_val = int(preferred_workout_duration)
                    except Exception:
                        return gr.update(value="Invalid workout duration value")
                    if user.preferred_workout_duration != duration_val:
                        user.preferred_workout_duration = duration_val
                        updated = True
                        msg.append(
                            f"Preferred workout duration updated to {duration_val}"
                        )

                if updated:
                    # Save changes
                    update_doc = user.model_dump()
                    update_doc["_rev"] = user_doc["_rev"]
                    db.save_document(update_doc, doc_id=user_id)
                    logger.info(f"Successfully saved profile changes: {msg}")
                    # Touch user_state to trigger Gradio change event
                    import datetime as _dt

                    now_str = _dt.datetime.now().isoformat()
                    if hasattr(user_state, "value") and isinstance(
                        user_state.value, dict
                    ):
                        user_state.value["_profile_updated"] = now_str
                    elif isinstance(user_state, dict):
                        user_state["_profile_updated"] = now_str
                    return None
                else:
                    logger.info("No changes to save")
                    return None

            except Exception as e:
                logger.error(f"Error saving profile: {str(e)}", exc_info=True)
                return gr.update(value=f"Error saving profile: {str(e)}")

        def add_injury(
            user_state, description, body_part, severity, date_injured, is_active, notes
        ):
            """Add a new injury to the user's profile."""
            logger.info(f"Adding injury with user state: {user_state}")
            if "id" not in user_state:
                logger.warning("No user id in user state provided when adding injury")
                return gr.update(value="Please log in to add injuries")

            if not description or not body_part:
                logger.warning("Missing required fields: description or body part")
                return gr.update(value="Description and Body Part are required")

            try:
                # Get current user document
                user_id = user_state["id"]
                if not user_id:
                    logger.error(
                        f"User ID not found in user state: {user_state}; cannot add injury"
                    )
                    return None

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
            if "id" not in user_state:
                return gr.update(value="Please log in to modify injuries")

            try:
                # Get current user document
                user_id = user_state["id"]
                if not user_id:
                    logger.error(
                        f"User ID not found in user state: {user_state}; cannot toggle injury active status"
                    )
                    return gr.update(value="Error: User profile not found")

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
            if "id" not in user_state:
                return gr.update(value="Please log in to delete injuries")

            try:
                # Get current user document
                user_id = user_state["id"]
                if not user_id:
                    logger.error(
                        f"User ID not found in user state: {user_state}; cannot delete injury"
                    )
                    return gr.update(value="Error: User profile not found")

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
                f"User state value type: {type(user_state) if hasattr(user_state, 'value') else 'No value attribute'}"
            )

            profile_updates = update_profile(user_state)
            return (*profile_updates,)

        # Connect profile load event
        load_data_btn.click(
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
            ],
        )

        # Update Hevy status and button states after saving API key
        save_hevy_key.click(
            fn=lambda user_state, hevy_api_key: save_profile(
                user_state, hevy_api_key=hevy_api_key
            ),
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
            ],
        )
        # Update user state and record with new weight
        weight_lbs.change(
            fn=lambda user_state, weight_lbs_val: save_profile(
                user_state, weight_lbs=weight_lbs_val
            ),
            inputs=[state["user_state"], weight_lbs],
            outputs=[],
        )
        # Update user state and record with new experience level
        experience.change(
            fn=lambda user_state, experience_val: save_profile(
                user_state, experience_level=experience_val
            ),
            inputs=[state["user_state"], experience],
            outputs=[],
        )
        # Update user state and record with new fitness goals
        goals.change(
            fn=lambda user_state, goals_val: save_profile(
                user_state, fitness_goals=goals_val
            ),
            inputs=[state["user_state"], goals],
            outputs=[],
        )
        # Update user state and record with new preferred workout days
        workout_days.change(
            fn=lambda user_state, days_val: save_profile(
                user_state, preferred_workout_days=days_val
            ),
            inputs=[state["user_state"], workout_days],
            outputs=[],
        )
        # Update user state and record with new preferred workout duration
        workout_duration.change(
            fn=lambda user_state, duration_val: save_profile(
                user_state, preferred_workout_duration=duration_val
            ),
            inputs=[state["user_state"], workout_duration],
            outputs=[],
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
            fn=lambda x: update_profile(x),
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
            fn=lambda x: update_profile(x),
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
            fn=lambda x: update_profile(x),
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

        logger.info("Profile view setup complete")

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
            load_data_btn,
            update_profile,  # renamed from load_profile
        )
