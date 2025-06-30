import logging
import os
from datetime import datetime, timedelta, timezone

import gradio as gr

from app.config.database import Database
from app.models.user import FitnessGoal, InjurySeverity, Sex, UnitSystem, UserProfile
from app.services.hevy_api import HevyAPI
from app.utils.crypto import encrypt_api_key
from app.utils.units import inches_to_cm, lbs_to_kg

# Configure logging
logger = logging.getLogger(__name__)

# Initialize database connection
db = Database()


def register_view(
    state,
    register_nav_button,
    login_nav_button,
    landing_nav_button,
    dashboard_nav_button,
    ai_recs_nav_button,
    profile_nav_button,
    logout_nav_button,
):
    with gr.Column():
        gr.Markdown("## Register")

        with gr.Row():
            username = gr.Textbox(label="Username", placeholder="Choose a username")
            email = gr.Textbox(label="Email", placeholder="Enter your email")

        with gr.Row():
            password = gr.Textbox(
                label="Password",
                placeholder="Enter your password",
                type="password",
                show_label=True,
                interactive=True,
                visible=True,
            )
            confirm_password = gr.Textbox(
                label="Confirm Password",
                placeholder="Confirm your password",
                type="password",
                show_label=True,
                interactive=True,
                visible=True,
            )

        with gr.Row():
            with gr.Column(scale=4):
                # Height in feet and inches
                height_feet = gr.Number(
                    label="Height (feet)", minimum=3, maximum=8, value=5
                )
                height_inches = gr.Number(
                    label="Height (inches)", minimum=0, maximum=11, value=10
                )
                # Weight in pounds
                weight_lbs = gr.Number(
                    label="Weight (lbs)", minimum=50, maximum=500, value=150
                )
                sex = gr.Dropdown(label="Sex", choices=[s.value for s in Sex])

            with gr.Column():
                age = gr.Number(label="Age", minimum=13, maximum=120, value=30)
                experience = gr.Dropdown(
                    label="Experience Level",
                    choices=["beginner", "intermediate", "advanced"],
                )
                preferred_units = gr.Dropdown(
                    label="Preferred Units",
                    choices=[unit.value for unit in UnitSystem],
                    value=UnitSystem.IMPERIAL.value,
                )
                goals = gr.CheckboxGroup(
                    label="Fitness Goals", choices=[g.value for g in FitnessGoal]
                )

        with gr.Row():
            preferred_workout_days = gr.Slider(
                label="Days per week you plan to work out",
                minimum=1,
                maximum=7,
                value=3,
                step=1,
            )
            preferred_workout_duration = gr.Slider(
                label="Preferred workout duration (minutes)",
                minimum=15,
                maximum=180,
                value=60,
                step=15,
            )

        # Injury Management Section
        gr.Markdown("### Injuries (Optional)")
        injuries = gr.State([])  # Store list of injuries

        with gr.Row():
            injury_description = gr.Textbox(
                label="Injury Description", placeholder="e.g., Left knee pain"
            )
            injury_body_part = gr.Textbox(
                label="Body Part", placeholder="e.g., Left knee"
            )
            injury_severity = gr.Dropdown(
                label="Severity",
                choices=[s.value for s in InjurySeverity],
                value=InjurySeverity.MILD.value,
            )
            injury_notes = gr.Textbox(
                label="Notes (Optional)",
                placeholder="Additional details about the injury",
            )

        with gr.Row():
            add_injury_btn = gr.Button("Add Injury")
            clear_injuries_btn = gr.Button("Clear All Injuries")

        injuries_list = gr.Markdown("No injuries added yet")

        def add_injury(description, body_part, severity, notes, current_injuries):
            if not description or not body_part:
                return current_injuries, gr.update(
                    value="Please fill in all required injury fields"
                )

            new_injury = {
                "description": description,
                "body_part": body_part,
                "severity": severity,
                "date_injured": datetime.now(timezone.utc).isoformat(),
                "is_active": True,
                "notes": notes if notes else None,
            }

            updated_injuries = current_injuries + [new_injury]
            injuries_text = "\n".join(
                [
                    f"- {i['description']} ({i['body_part']}, {i['severity']})"
                    for i in updated_injuries
                ]
            )

            return updated_injuries, gr.update(value=injuries_text)

        def clear_injuries():
            return [], gr.update(value="No injuries added yet")

        add_injury_btn.click(
            fn=add_injury,
            inputs=[
                injury_description,
                injury_body_part,
                injury_severity,
                injury_notes,
                injuries,
            ],
            outputs=[injuries, injuries_list],
        )

        clear_injuries_btn.click(
            fn=clear_injuries, inputs=[], outputs=[injuries, injuries_list]
        )

        # Hevy API Integration
        gr.Markdown("### Hevy API Integration (Optional)")
        hevy_api_key = gr.Textbox(
            label="Hevy API Key",
            placeholder="You can add this later in your profile",
            type="password",
        )

        with gr.Row():
            register_button = gr.Button("Register", variant="primary")
            error_message = gr.Markdown(visible=False)

        def handle_register_and_route(
            username,
            email,
            password,
            confirm_password,
            height_feet,
            height_inches,
            weight_lbs,
            sex,
            age,
            experience,
            preferred_units,
            goals,
            preferred_workout_days,
            preferred_workout_duration,
            injuries,
            hevy_api_key,
            user_state,
        ):
            user, error_msg, encrypted_key = page_handle_register(
                username,
                email,
                password,
                confirm_password,
                height_feet,
                height_inches,
                weight_lbs,
                sex,
                age,
                experience,
                preferred_units,
                goals,
                preferred_workout_days,
                preferred_workout_duration,
                injuries,
                hevy_api_key,
            )
            if user is None or not isinstance(user, dict) or "id" not in user:
                error_text = (
                    error_msg
                    if error_msg
                    else "Registration failed. Please check your input and try again."
                )
                return (
                    {},
                    *state["update_nav_visibility"](None),
                    "register",
                    gr.update(value=error_text, visible=True),
                )
            # Registration successful
            if encrypted_key:
                import threading

                from app.services.sync import sync_hevy_data

                threading.Thread(
                    target=sync_hevy_data, args=(user,), daemon=True
                ).start()
            return (
                user,
                *state["update_nav_visibility"](user),
                "dashboard",
                gr.update(value="", visible=False),
            )

        # Register button click event (moved from routes.py)
        register_button.click(
            fn=handle_register_and_route,
            inputs=[
                username,
                email,
                password,
                confirm_password,
                height_feet,
                height_inches,
                weight_lbs,
                sex,
                age,
                experience,
                preferred_units,
                goals,
                preferred_workout_days,
                preferred_workout_duration,
                injuries,
                hevy_api_key,
                state["user_state"],
            ],
            outputs=[
                state["user_state"],
                register_nav_button,
                login_nav_button,
                landing_nav_button,
                dashboard_nav_button,
                ai_recs_nav_button,
                profile_nav_button,
                logout_nav_button,
                state["current_page"],
                error_message,
            ],
        )

        def page_handle_register(
            username,
            email,
            password,
            confirm_password,
            height_feet,
            height_inches,
            weight_lbs,
            sex,
            age,
            experience,
            preferred_units,
            goals,
            preferred_workout_days,
            preferred_workout_duration,
            injuries,
            hevy_api_key,
        ):
            try:
                if password != confirm_password:
                    return (
                        {},
                        gr.update(value="Passwords do not match", visible=True),
                        None,
                    )
                # Check if username already exists
                if db.username_exists(username):
                    return (
                        {},
                        gr.update(
                            value="Username already exists. Please choose a different username.",
                            visible=True,
                        ),
                        None,
                    )
                # Convert height to cm
                height_cm = inches_to_cm(height_feet * 12 + height_inches)
                # Convert weight to kg
                weight_kg = lbs_to_kg(weight_lbs)
                # Handle API key logic
                ENV = os.getenv("ENV", "development")
                encrypted_key = None
                if not hevy_api_key or not hevy_api_key.strip():
                    if ENV in ["development", "beta"]:
                        default_key = os.getenv("HEVY_API_KEY")
                        if default_key:
                            hevy_api_key = default_key
                if hevy_api_key and hevy_api_key.strip():
                    try:
                        encrypted_key = encrypt_api_key(hevy_api_key)
                    except Exception as e:
                        return (
                            {},
                            gr.update(
                                value=f"Error encrypting Hevy API key: {str(e)}",
                                visible=True,
                            ),
                            None,
                        )
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
                    preferred_units=UnitSystem(preferred_units),
                    hevy_api_key=encrypted_key,
                    injuries=injuries,
                )
                # Save to database
                user_dict = new_user.model_dump()
                doc_id, doc_rev = db.save_document(user_dict)
                # Return user object for state management
                user = {"id": doc_id, "username": username, "email": email}
                return user, gr.update(visible=False), encrypted_key
            except Exception as e:
                logger.error(f"Registration failed: {str(e)}", exc_info=True)
                return (
                    {},
                    gr.update(value=f"Registration failed: {str(e)}", visible=True),
                    None,
                )

        return register_button, error_message, page_handle_register
