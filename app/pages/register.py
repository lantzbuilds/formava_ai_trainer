import logging
from datetime import datetime, timedelta, timezone

import gradio as gr

from app.config.database import Database
from app.models.user import FitnessGoal, InjurySeverity, Sex, UserProfile
from app.services.hevy_api import HevyAPI
from app.utils.crypto import encrypt_api_key
from app.utils.units import inches_to_cm, lbs_to_kg

# Configure logging
logger = logging.getLogger(__name__)

# Initialize database connection
db = Database()


def register_view():
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

        def handle_register(
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
            goals,
            preferred_workout_days,
            preferred_workout_duration,
            injuries,
            hevy_api_key,
        ):
            try:
                if password != confirm_password:
                    return None, gr.update(value="Passwords do not match", visible=True)

                # Check if username already exists
                if db.username_exists(username):
                    return None, gr.update(
                        value="Username already exists. Please choose a different username.",
                        visible=True,
                    )

                # Convert height to cm
                height_cm = inches_to_cm(height_feet * 12 + height_inches)
                # Convert weight to kg
                weight_kg = lbs_to_kg(weight_lbs)

                # Handle API key encryption
                encrypted_key = None
                if hevy_api_key and hevy_api_key.strip():
                    try:
                        encrypted_key = encrypt_api_key(hevy_api_key)
                    except Exception as e:
                        return None, gr.update(
                            value=f"Error encrypting Hevy API key: {str(e)}",
                            visible=True,
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
                    hevy_api_key=encrypted_key,
                    injuries=injuries,
                )

                # Save to database
                user_dict = new_user.model_dump()
                doc_id, doc_rev, hevy_api_key = db.save_document(user_dict)
                encrypted_key = hevy_api_key

                # Return user object for state management
                user = {"id": doc_id, "username": username, "email": email}
                # Sync workouts from Hevy API
                # if encrypted_key:
                #     try:
                #         logger.info(f"Initializing Hevy API sync for user {username}")
                #         hevy_api = HevyAPI(api_key=encrypted_key, is_encrypted=True)

                #         # Get workouts from the last 30 days for initial sync
                #         end_date = datetime.now(timezone.utc)
                #         start_date = end_date - timedelta(days=30)

                #         logger.info(
                #             f"Fetching workouts from {start_date} to {end_date}"
                #         )
                #         all_workouts = hevy_api.get_workouts(
                #             start_date=start_date, end_date=end_date
                #         )

                #         if all_workouts:
                #             logger.info(f"Found {len(all_workouts)} workouts to sync")
                #             db.save_user_workouts(doc_id, all_workouts)
                #             logger.info(
                #                 f"Successfully synced {len(all_workouts)} workouts for user {username}"
                #             )
                #         else:
                #             logger.info(
                #                 f"No workouts found for user {username} in the last 30 days"
                #             )

                #     except Exception as e:
                #         logger.error(
                #             f"Error syncing Hevy workouts for user {username}: {str(e)}"
                #         )
                #         # Continue with registration even if sync fails
                #         logger.info("Continuing with registration despite sync error")

                return user, gr.update(visible=False)

            except Exception as e:
                logger.error(f"Registration failed: {str(e)}", exc_info=True)
                return None, gr.update(
                    value=f"Registration failed: {str(e)}", visible=True
                )

        register_button.click(
            fn=handle_register,
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
                goals,
                preferred_workout_days,
                preferred_workout_duration,
                injuries,
                hevy_api_key,
            ],
            outputs=[gr.State(), error_message],
        )

        return register_button, error_message
