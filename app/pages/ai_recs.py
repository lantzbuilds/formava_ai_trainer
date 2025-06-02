import logging
from datetime import datetime, timedelta, timezone

import gradio as gr

from app.config.database import Database
from app.models.user import UserProfile
from app.services.hevy_api import HevyAPI
from app.services.openai_service import OpenAIService
from app.services.routine_folder_builder import RoutineFolderBuilder
from app.services.vector_store import ExerciseVectorStore
from app.utils.formatters import format_routine_markdown

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize services
db = Database()
openai_service = OpenAIService()
vector_store = ExerciseVectorStore()


def ai_recs_view(state):
    """Display the AI recommendations page."""
    with gr.Column():
        # Title
        gr.Markdown("# AI Recommendations")

        # User Profile Summary Section
        with gr.Group():
            gr.Markdown("## Your Profile Summary")
            profile_summary = gr.Markdown()

        # Workout History Summary Section
        with gr.Group():
            gr.Markdown("## Recent Workout History")
            workout_summary = gr.Markdown()

        # Available Exercises Summary Section
        with gr.Group():
            gr.Markdown("## Available Exercises")
            exercises_summary = gr.Markdown()

        # Routine Generation Preferences Section
        with gr.Group():
            gr.Markdown("## Routine Generation Preferences")

            with gr.Row():
                split_type = gr.Dropdown(
                    choices=["auto", "full_body", "upper_lower", "push_pull"],
                    label="Workout Split Type",
                    info="Choose how to split your workouts. 'auto' will determine based on your experience level and days per week.",
                )

                period = gr.Dropdown(
                    choices=["week", "month"],
                    label="Time Period",
                    info="Generate routines for the upcoming week or month",
                )

                include_cardio = gr.Checkbox(
                    label="Include Cardio",
                    value=True,
                    info="Include cardio exercises in the generated routines",
                )

            routine_title = gr.Textbox(
                label="Routine Folder Title",
                info="Edit the title for your workout routine folder",
            )

            generate_btn = gr.Button("Generate Recommendations")

        # Generated Routine Display Section
        with gr.Group():
            gr.Markdown("## Generated Routine")
            routine_display = gr.Markdown()

        # Save to Hevy Section
        with gr.Group():
            save_btn = gr.Button("Save to Hevy")
            save_status = gr.Markdown()

        # Add a hidden button for initial data loading
        load_data_btn = gr.Button("Load Data", visible=False)

        def load_user_data(user_state):
            """Load and display user data."""
            if not user_state:
                return (
                    "Please log in to view recommendations.",
                    "Please log in to view workout history.",
                    "Please log in to view available exercises.",
                    "Auto Workout Plan - Next Week",
                )

            # Get user document from database
            user_id = (
                user_state.value.get("id")
                if hasattr(user_state, "value")
                else user_state.get("id")
            )
            if not user_id:
                return (
                    "User ID not found in state",
                    "User ID not found in state",
                    "User ID not found in state",
                    "Auto Workout Plan - Next Week",
                )

            user_doc = db.get_document(user_id)
            if not user_doc:
                return (
                    "User profile not found",
                    "User profile not found",
                    "User profile not found",
                    "Auto Workout Plan - Next Week",
                )

            # Create UserProfile instance
            user = UserProfile(**user_doc)

            # Build profile summary
            profile_text = f"""
            **Experience Level:** {user.experience_level}
            **Fitness Goals:** {', '.join([g.value for g in user.fitness_goals])}
            **Workout Schedule:** {user.preferred_workout_days} days per week
            **Preferred Duration:** {user.preferred_workout_duration} minutes
            """

            if user.injuries:
                profile_text += "\n**Active Injuries:**"
                for injury in user.injuries:
                    if injury.is_active:
                        profile_text += f"\n- {injury.description} ({injury.body_part})"
            else:
                profile_text += "\n**No active injuries**"

            # Get user's recent workouts
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=30)
            workouts = db.get_user_workout_history(user_id, start_date, end_date)

            # Build workout summary
            if workouts:
                workout_count = len(workouts)
                total_exercises = sum(len(w.get("exercises", [])) for w in workouts)
                avg_exercises = (
                    total_exercises / workout_count if workout_count > 0 else 0
                )

                workout_text = f"""
                **Workouts in last 30 days:** {workout_count}
                **Average exercises per workout:** {avg_exercises:.1f}
                """
            else:
                workout_text = "**No workouts recorded in the last 30 days**"

            # Get available exercises count
            exercises = db.get_exercises(user_id=user_id, include_custom=True)
            exercises_text = f"**Total exercises available:** {len(exercises)}"

            # Set default routine title
            date_range = RoutineFolderBuilder.get_date_range("week")
            default_title = f"Auto Workout Plan - {date_range}"

            return profile_text, workout_text, exercises_text, default_title

        def generate_routine(user_state, split, period, cardio, title):
            """Generate workout routine."""
            if not user_state:
                return "Please log in to generate recommendations."

            try:
                # Get user document
                user_id = (
                    user_state.value.get("id")
                    if hasattr(user_state, "value")
                    else user_state.get("id")
                )
                if not user_id:
                    return "User ID not found in state"

                user_doc = db.get_document(user_id)
                if not user_doc:
                    return "User profile not found"

                user = UserProfile(**user_doc)

                # Create context for routine generation
                context = {
                    "user_id": user_id,
                    "user_profile": {
                        "experience_level": user.experience_level,
                        "fitness_goals": [g.value for g in user.fitness_goals],
                        "preferred_workout_duration": user.preferred_workout_duration,
                        "injuries": [
                            {
                                "description": i.description,
                                "body_part": i.body_part,
                                "is_active": i.is_active,
                            }
                            for i in user.injuries
                        ],
                        "workout_schedule": {
                            "days_per_week": user.preferred_workout_days,
                        },
                    },
                    "generation_preferences": {
                        "split_type": split,
                        "include_cardio": cardio,
                    },
                }

                # Generate the routine folder
                routine_folder = openai_service.generate_routine_folder(
                    name=title,
                    description="Personalized workout plan based on your profile and goals",
                    context=context,
                    period=period,
                )

                if routine_folder:
                    # Store the generated routine in state
                    state["generated_routine"] = routine_folder

                    # Format the routine for display
                    display_text = f"## {routine_folder['name']}\n"
                    display_text += f"*{routine_folder['description']}*\n\n"
                    display_text += f"**Split Type:** {routine_folder['split_type'].replace('_', ' ').title()}\n"
                    display_text += (
                        f"**Days per Week:** {routine_folder['days_per_week']}\n"
                    )
                    display_text += f"**Period:** {routine_folder['period'].title()}\n"
                    display_text += (
                        f"**Date Range:** {routine_folder['date_range']}\n\n"
                    )

                    for routine in routine_folder["routines"]:
                        display_text += "---\n"
                        display_text += format_routine_markdown(routine)

                    return display_text
                else:
                    return "Failed to generate routine folder. Please try again."

            except Exception as e:
                logger.error(f"Error generating recommendations: {str(e)}")
                return f"Error generating recommendations: {str(e)}"

        def save_to_hevy(user_state):
            """Save generated routine to Hevy."""
            if not user_state:
                return "Please log in to save to Hevy."

            try:
                # Get user document
                user_id = (
                    user_state.value.get("id")
                    if hasattr(user_state, "value")
                    else user_state.get("id")
                )
                if not user_id:
                    return "User ID not found in state"

                user_doc = db.get_document(user_id)
                if not user_doc:
                    return "User profile not found"

                user = UserProfile(**user_doc)

                if not user.hevy_api_key:
                    return "Hevy API key is not configured. Please configure it in your profile."

                hevy_api = HevyAPI(api_key=user.hevy_api_key, is_encrypted=True)
                saved_folder = hevy_api.save_routine_folder(
                    routine_folder=state["generated_routine"],
                    user_id=user_id,
                    db=db,
                )

                if saved_folder:
                    return "Routine folder saved to Hevy successfully!"
                else:
                    return "Failed to save routine folder to Hevy. Please try again."

            except Exception as e:
                logger.error(f"Error saving to Hevy: {str(e)}")
                return f"Error saving to Hevy: {str(e)}"

        # Set up event handlers
        generate_btn.click(
            fn=generate_routine,
            inputs=[
                state["user_state"],
                split_type,
                period,
                include_cardio,
                routine_title,
            ],
            outputs=routine_display,
        )

        save_btn.click(
            fn=save_to_hevy, inputs=[state["user_state"]], outputs=save_status
        )

        # Load initial data when page is shown
        load_data_btn.click(
            fn=load_user_data,
            inputs=[state["user_state"]],
            outputs=[
                profile_summary,
                workout_summary,
                exercises_summary,
                routine_title,
            ],
        )

        return [
            profile_summary,
            workout_summary,
            exercises_summary,
            routine_display,
            save_status,
            load_data_btn,
            load_user_data,
        ]
